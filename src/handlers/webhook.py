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

            # 3. Processar mensagem com agente
            response = await process_message(message)

            span.set_attribute("intent", response.intent.value)
            span.set_attribute("confidence", response.confidence)
            span.set_attribute("trace_id", response.trace_id)

            # 4. Enviar resposta (assíncrono)
            background_tasks.add_task(
                send_whatsapp_reply,
                message.from_number,
                response.reply_text,
            )

            # 5. Marcar como processado no Redis
            try:
                idempotency = get_idempotency_manager()
                await idempotency.mark_processed(
                    message.message_id,
                    {"intent": response.intent.value},
                )
            except Exception:
                pass

            logger.info(
                "webhook_processed",
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

