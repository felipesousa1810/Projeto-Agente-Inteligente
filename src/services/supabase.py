"""Supabase Client - Database operations."""

from typing import Any

from src.config.settings import get_settings
from src.utils.logger import get_logger
from supabase import Client, create_client

logger = get_logger(__name__)

# Global client instance
_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Get or create Supabase client instance.

    Returns:
        Supabase Client instance.

    Raises:
        ValueError: If Supabase credentials are not configured.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_key:
        logger.warning(
            "supabase_not_configured",
            message="Supabase credentials not set. Database operations will fail.",
        )
        # Return a mock or raise based on environment
        if settings.is_development:
            logger.info("supabase_mock_mode", message="Using mock mode in development")
            # We'll still try to create - will fail gracefully
        else:
            raise ValueError("Supabase credentials are required in production")

    _supabase_client = create_client(
        settings.supabase_url,
        settings.supabase_key,
    )

    logger.info("supabase_client_created")
    return _supabase_client


async def get_or_create_customer(phone_number: str) -> dict[str, Any]:
    """Get existing customer or create new one.

    Args:
        phone_number: Customer's phone number in E.164 format.

    Returns:
        Customer record dict.
    """
    client = get_supabase_client()

    # Try to find existing customer
    result = (
        client.table("customers")
        .select("*")
        .eq("phone_number", phone_number)
        .maybe_single()
        .execute()
    )

    if result.data:
        logger.info(
            "customer_found",
            customer_id=result.data["id"],
            phone_number=phone_number,
        )
        return result.data

    # Create new customer
    new_customer = {"phone_number": phone_number}
    result = client.table("customers").insert(new_customer).execute()

    logger.info(
        "customer_created",
        customer_id=result.data[0]["id"],
        phone_number=phone_number,
    )
    return result.data[0]


async def save_message(
    message_id: str,
    customer_id: str,
    direction: str,
    body: str,
    intent: str | None,
    trace_id: str,
) -> dict[str, Any]:
    """Save message to database.

    Args:
        message_id: Unique message ID.
        customer_id: Customer UUID.
        direction: 'incoming' or 'outgoing'.
        body: Message text.
        intent: Detected intent (for incoming).
        trace_id: Trace ID for observability.

    Returns:
        Saved message record.
    """
    client = get_supabase_client()

    message_data = {
        "message_id": message_id,
        "customer_id": customer_id,
        "direction": direction,
        "body": body,
        "intent": intent,
        "trace_id": trace_id,
    }

    result = client.table("messages").insert(message_data).execute()

    logger.info(
        "message_saved",
        message_id=message_id,
        direction=direction,
        trace_id=trace_id,
    )
    return result.data[0]


async def create_appointment(
    customer_id: str,
    scheduled_date: str,
    scheduled_time: str,
    confirmation_code: str,
) -> dict[str, Any]:
    """Create appointment in database.

    Args:
        customer_id: Customer UUID.
        scheduled_date: Date in YYYY-MM-DD format.
        scheduled_time: Time in HH:MM format.
        confirmation_code: Unique confirmation code.

    Returns:
        Created appointment record.
    """
    client = get_supabase_client()

    appointment_data = {
        "customer_id": customer_id,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "status": "scheduled",
        "confirmation_code": confirmation_code,
    }

    result = client.table("appointments").insert(appointment_data).execute()

    logger.info(
        "appointment_created",
        appointment_id=result.data[0]["id"],
        confirmation_code=confirmation_code,
    )
    return result.data[0]


async def get_appointment_by_code(confirmation_code: str) -> dict[str, Any] | None:
    """Get appointment by confirmation code.

    Args:
        confirmation_code: Unique confirmation code.

    Returns:
        Appointment record or None if not found.
    """
    client = get_supabase_client()

    result = (
        client.table("appointments")
        .select("*")
        .eq("confirmation_code", confirmation_code)
        .maybe_single()
        .execute()
    )

    return result.data


async def cancel_appointment(appointment_id: str) -> dict[str, Any]:
    """Cancel appointment by ID.

    Args:
        appointment_id: Appointment UUID.

    Returns:
        Updated appointment record.
    """
    client = get_supabase_client()

    result = (
        client.table("appointments")
        .update({"status": "canceled"})
        .eq("id", appointment_id)
        .execute()
    )

    logger.info(
        "appointment_canceled",
        appointment_id=appointment_id,
    )
    return result.data[0]


async def get_appointments_for_date(check_date: str) -> list[dict[str, Any]]:
    """Get all appointments for a specific date.

    Args:
        check_date: Date in YYYY-MM-DD format.

    Returns:
        List of appointment records.
    """
    client = get_supabase_client()

    result = (
        client.table("appointments")
        .select("*")
        .eq("scheduled_date", check_date)
        .neq("status", "canceled")  # Exclude canceled appointments
        .execute()
    )

    logger.info(
        "appointments_fetched_for_date",
        date=check_date,
        count=len(result.data),
    )
    return result.data
