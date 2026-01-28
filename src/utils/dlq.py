"""Dead Letter Queue - Failed message handling."""

from typing import Any

from src.contracts.whatsapp_message import WhatsAppMessage
from src.services.observability import get_current_trace_id
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def send_to_dlq(
    message: WhatsAppMessage,
    error: str,
    error_type: str = "processing_error",
) -> None:
    """Envia mensagem falha para Dead Letter Queue.

    Args:
        message: Mensagem original que falhou.
        error: Descrição do erro.
        error_type: Tipo/categoria do erro.
    """
    trace_id = get_current_trace_id() or "unknown"

    # Log the failure
    logger.error(
        "message_sent_to_dlq",
        message_id=message.message_id,
        from_number=message.from_number,
        error_type=error_type,
        error=error,
        trace_id=trace_id,
    )

    # Try to persist to database
    try:
        from src.services.supabase import get_supabase_client

        supabase = get_supabase_client()

        dlq_entry = {
            "message_id": message.message_id,
            "error_type": error_type,
            "error_message": error,
            "payload": message.model_dump_json(),
            "trace_id": trace_id,
            "retried": False,
        }

        await supabase.table("dead_letter_queue").insert(dlq_entry).execute()

        logger.info(
            "dlq_entry_persisted",
            message_id=message.message_id,
            trace_id=trace_id,
        )

    except Exception as e:
        # Log but don't raise - DLQ persistence failure shouldn't break the flow
        logger.error(
            "dlq_persistence_failed",
            message_id=message.message_id,
            error=str(e),
        )


async def get_dlq_entries(
    limit: int = 100,
    include_retried: bool = False,
) -> list[dict[str, Any]]:
    """Recupera entradas da DLQ para reprocessamento.

    Args:
        limit: Número máximo de entradas.
        include_retried: Incluir entradas já reprocessadas.

    Returns:
        Lista de entradas da DLQ.
    """
    try:
        from src.services.supabase import get_supabase_client

        supabase = get_supabase_client()

        query = supabase.table("dead_letter_queue").select("*")

        if not include_retried:
            query = query.eq("retried", False)

        result = query.order("created_at").limit(limit).execute()

        return result.data

    except Exception as e:
        logger.error(
            "dlq_fetch_failed",
            error=str(e),
        )
        return []


async def mark_as_retried(dlq_id: str) -> None:
    """Marca entrada da DLQ como reprocessada.

    Args:
        dlq_id: ID da entrada na DLQ.
    """
    try:
        from src.services.supabase import get_supabase_client

        supabase = get_supabase_client()

        await (
            supabase.table("dead_letter_queue")
            .update({"retried": True})
            .eq("id", dlq_id)
            .execute()
        )

        logger.info(
            "dlq_entry_marked_retried",
            dlq_id=dlq_id,
        )

    except Exception as e:
        logger.error(
            "dlq_mark_retried_failed",
            dlq_id=dlq_id,
            error=str(e),
        )
