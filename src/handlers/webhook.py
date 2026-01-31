"""Webhook Handler - WhatsApp webhook endpoint."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.config.settings import get_settings
from src.contracts.whatsapp_message import EvolutionWebhook, WhatsAppMessage
from src.core.agent import process_message
from src.core.idempotency import IdempotencyManager
from src.services.evolution import send_whatsapp_reply
from src.services.observability import get_tracer
from src.utils.dlq import send_to_dlq
from src.utils.logger import get_logger

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = get_logger(__name__)
tracer = get_tracer(__name__)

# Idempotency manager (initialized lazily)
_idempotency_manager: IdempotencyManager | None = None


def get_idempotency_manager() -> IdempotencyManager:
    """Get or create idempotency manager."""
    global _idempotency_manager
    if _idempotency_manager is None:
        settings = get_settings()
        _idempotency_manager = IdempotencyManager(
            redis_url=settings.redis_url,
            ttl_seconds=86400,
        )
    return _idempotency_manager


@router.post("/whatsapp")
async def whatsapp_webhook(
    payload: EvolutionWebhook,
    background_tasks: BackgroundTasks,
) -> dict:
    """Webhook handler para Evolution API (WhatsApp).

    Recebe payload da Evolution API, converte para mensagem interna,
    processa com o agente e envia resposta.

    Args:
        payload: Payload da Evolution API (messages.upsert).
        background_tasks: FastAPI background tasks.

    Returns:
        Dict com status.
    """
    # 1. Converter payload para mensagem interna
    message = WhatsAppMessage.from_evolution(payload)

    if not message:
        # Ignorar eventos irrelevantes (mensagens enviadas por mim, status, etc)
        return {"status": "ignored", "reason": "filtered_event"}

    # Iniciar tracing com dados normalizados
    with tracer.start_as_current_span("whatsapp_webhook") as span:
        span.set_attribute("message_id", message.message_id)
        span.set_attribute("from_number", message.from_number)
        span.set_attribute("event", payload.event)

        try:
            # 2. Verificar idempotência (fail open se Redis indisponível)
            try:
                idempotency = get_idempotency_manager()
                is_duplicate, cached = await idempotency.check_and_mark(
                    message.message_id
                )
                if is_duplicate:
                    span.set_attribute("duplicate", True)
                    logger.info(
                        "duplicate_message_blocked",
                        message_id=message.message_id,
                    )
                    return {
                        "status": "duplicate",
                        "processed": False,
                        "message": "Message already processed",
                    }
            except Exception as redis_err:
                logger.warning(
                    "idempotency_check_skipped",
                    error=str(redis_err),
                )

            # 3. Criar ou Obter Cliente (Garantir que cliente existe)
            from src.core.dependencies import AppDependencies
            from src.services.supabase import get_supabase_service

            supabase_service = get_supabase_service()

            try:
                # Precisamos do ID do cliente para a tabela de mensagens
                customer = await supabase_service.get_or_create_customer(
                    message.from_number
                )
                customer_id = customer["id"]
            except Exception as db_err:
                logger.error("falha_criacao_cliente", error=str(db_err))
                # Fallback ou falha graciosa?
                # Por enquanto, propagar o erro pois precisamos do cliente
                raise db_err

            # Criar objeto de dependências
            deps = AppDependencies(
                supabase=supabase_service,
                customer_id=message.from_number,
                trace_id=span.get_span_context().trace_id or "unknown",
            )

            # 4. Salvar mensagem de ENTRADA
            try:
                await supabase_service.save_message(
                    message_id=message.message_id,
                    customer_id=customer_id,
                    direction="incoming",
                    body=message.body,
                    intent=None,  # Será atualizado depois ou salvo como está
                    trace_id=deps.trace_id,
                )
            except Exception as save_err:
                logger.error("falha_salvar_entrada", error=str(save_err))
                # Não bloquear processamento se salvar falhar, apenas logar

            # 5. Processar mensagem com agente
            response = await process_message(message, deps=deps)

            span.set_attribute("intent", response.intent.value)
            span.set_attribute("confidence", response.confidence)
            span.set_attribute("trace_id", response.trace_id)

            # 6. Salvar mensagem de SAÍDA (Resposta)
            try:
                # Gerar ID único para mensagem de saída
                import uuid

                outgoing_id = f"MSG-{uuid.uuid4().hex[:16].upper()}"

                await supabase_service.save_message(
                    message_id=outgoing_id,
                    customer_id=customer_id,
                    direction="outgoing",
                    body=response.reply_text,
                    intent=response.intent.value,
                    trace_id=response.trace_id,
                )
            except Exception as save_out_err:
                logger.error("falha_salvar_saida", error=str(save_out_err))

            # 7. Enviar resposta (assíncrono)
            background_tasks.add_task(
                send_whatsapp_reply,
                message.from_number,
                response.reply_text,
            )

            # 8. Marcar como processado no Redis
            try:
                idempotency = get_idempotency_manager()
                await idempotency.mark_processed(
                    message.message_id,
                    {"intent": response.intent.value},
                )
            except Exception:
                pass

            logger.info(
                "webhook_processado",
                message_id=message.message_id,
                trace_id=response.trace_id,
                intent=response.intent.value,
            )

            return {
                "status": "success",
                "trace_id": response.trace_id,
                "intent": response.intent.value,
                "confidence": response.confidence,
            }

        except Exception as e:
            span.record_exception(e)

            logger.error(
                "webhook_processing_failed",
                message_id=message.message_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Send to DLQ in background
            background_tasks.add_task(
                send_to_dlq,
                message,
                str(e),
                type(e).__name__,
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Processing failed",
                    "message_id": message.message_id,
                },
            ) from e


@router.get("/health")
async def webhook_health() -> dict:
    """Health check for webhook endpoint.

    Returns:
        Health status dict.
    """
    return {"status": "healthy", "endpoint": "webhook"}


def _normalize_phone(phone: str) -> str:
    """Normalize phone to E.164 format (same as WhatsAppMessage validator).

    Args:
        phone: Phone number in any format.

    Returns:
        Phone in E.164 format (e.g., +5511999999999).
    """
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    if not cleaned.startswith("+"):
        cleaned = f"+{cleaned}"
    return cleaned


@router.delete("/debug/clear-context/{phone}")
async def clear_context(phone: str) -> dict:
    """Clear conversation context for a phone number (debug/testing only).

    Args:
        phone: Phone number to clear context for.

    Returns:
        Status dict.
    """
    from src.services.conversation_state import get_conversation_state_manager

    # Normalize phone to match Redis key format
    normalized_phone = _normalize_phone(phone)

    try:
        state_manager = get_conversation_state_manager()
        await state_manager.clear(normalized_phone)
        logger.info("debug_context_cleared", phone=normalized_phone)
        return {
            "status": "success",
            "message": f"Context cleared for {normalized_phone}",
            "normalized_phone": normalized_phone,
        }
    except Exception as e:
        logger.error("debug_context_clear_failed", phone=normalized_phone, error=str(e))
        return {"status": "error", "message": str(e)}


@router.get("/debug/get-context/{phone}")
async def get_context(phone: str) -> dict:
    """Get conversation context for a phone number (debug/testing only).

    Args:
        phone: Phone number to get context for.

    Returns:
        Context data dict.
    """
    from src.services.conversation_state import get_conversation_state_manager

    # Normalize phone to match Redis key format
    normalized_phone = _normalize_phone(phone)

    try:
        state_manager = get_conversation_state_manager()
        fsm = await state_manager.get_or_create(normalized_phone)
        return {
            "status": "success",
            "phone": normalized_phone,
            "current_state": fsm.current_state.value,
            "collected_data": fsm.collected_data,
            "history": [s.value for s in fsm.history],
        }
    except Exception as e:
        logger.error("debug_context_get_failed", phone=normalized_phone, error=str(e))
        return {"status": "error", "message": str(e)}


@router.get("/debug/list-contexts")
async def list_contexts() -> dict:
    """List all active conversation contexts (debug/testing only).

    Returns:
        List of phone numbers with active contexts.
    """
    import json

    import redis.asyncio as redis_client

    from src.config.settings import get_settings

    settings = get_settings()

    try:
        r = redis_client.from_url(settings.redis_url)
        keys = await r.keys("conversation:*")

        contexts = []
        for key in keys[:20]:  # Limit to 20 to avoid overload
            key_str = key.decode() if isinstance(key, bytes) else key
            phone = key_str.replace("conversation:", "")

            # Get context data
            data = await r.get(key)
            if data:
                data_str = data.decode() if isinstance(data, bytes) else data
                context = json.loads(data_str)
                contexts.append(
                    {
                        "phone": phone,
                        "state": context.get("current_state", "unknown"),
                        "collected_data": context.get("collected_data", {}),
                    }
                )

        await r.aclose()

        return {
            "status": "success",
            "count": len(contexts),
            "contexts": contexts,
        }
    except Exception as e:
        logger.error("debug_list_contexts_failed", error=str(e))
        return {"status": "error", "message": str(e)}
