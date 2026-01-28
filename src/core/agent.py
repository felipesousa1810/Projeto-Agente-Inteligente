"""Pydantic AI Agent - Deterministic scheduling agent."""

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.config.agent_config import AgentConfig
from src.config.settings import get_settings
from src.contracts.agent_response import AgentResponse, IntentType
from src.contracts.whatsapp_message import WhatsAppMessage
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Agent dependencies (injected at runtime)
class AgentDependencies:
    """Dependencies injected into agent tools."""

    def __init__(
        self,
        customer_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Initialize dependencies.

        Args:
            customer_id: ID of the customer.
            trace_id: Trace ID for observability.
        """
        self.customer_id = customer_id
        self.trace_id = trace_id or str(uuid.uuid4())


def create_agent(
    config: AgentConfig | None = None,
) -> Agent[AgentDependencies, dict[str, Any]]:
    """Create and configure the Pydantic AI agent.

    Args:
        config: Optional agent configuration. Uses defaults if not provided.

    Returns:
        Configured Agent instance.
    """
    if config is None:
        config = AgentConfig()

    settings = get_settings()

    # Create OpenAI model with deterministic settings
    model = OpenAIModel(
        config.model,
        # api_key is automatically loaded from OPENAI_API_KEY env var
    )


    # Create agent
    agent: Agent[AgentDependencies, dict[str, Any]] = Agent(
        model=model,
        system_prompt=config.system_prompt,
        deps_type=AgentDependencies,
        retries=0,  # External retry control
    )

    # Register tools
    @agent.tool
    async def check_availability(
        ctx: RunContext[AgentDependencies],
        date_str: str,
        time_str: str,
    ) -> dict[str, Any]:
        """Verifica disponibilidade de horário.

        Args:
            ctx: Run context with dependencies.
            date_str: Data no formato YYYY-MM-DD.
            time_str: Hora no formato HH:MM.

        Returns:
            Dict com 'available' (bool) e 'alternatives' (list).
        """
        logger.info(
            "check_availability",
            trace_id=ctx.deps.trace_id,
            date=date_str,
            time=time_str,
        )

        # Parse date and time
        try:
            check_date = date.fromisoformat(date_str)
            check_time = time.fromisoformat(time_str)
        except ValueError:
            return {
                "available": False,
                "error": "Formato de data/hora inválido",
                "alternatives": [],
            }

        # Check if date is in the future
        if check_date < date.today():
            return {
                "available": False,
                "error": "Data no passado",
                "alternatives": [],
            }

        # TODO: Implement actual availability check with database
        # For now, simulate availability
        hour = check_time.hour

        # Business hours: 8:00 - 18:00
        if hour < 8 or hour >= 18:
            return {
                "available": False,
                "error": "Fora do horário comercial (8h-18h)",
                "alternatives": ["09:00", "10:00", "14:00", "15:00"],
            }

        return {
            "available": True,
            "alternatives": [],
        }

    @agent.tool
    async def create_appointment(
        ctx: RunContext[AgentDependencies],
        date_str: str,
        time_str: str,
    ) -> dict[str, Any]:
        """Cria um novo agendamento.

        Args:
            ctx: Run context with dependencies.
            date_str: Data no formato YYYY-MM-DD.
            time_str: Hora no formato HH:MM.

        Returns:
            Dict com 'success', 'appointment_id' e 'confirmation_code'.
        """
        logger.info(
            "create_appointment",
            trace_id=ctx.deps.trace_id,
            customer_id=ctx.deps.customer_id,
            date=date_str,
            time=time_str,
        )

        # Generate confirmation code
        confirmation_code = f"APPT-{uuid.uuid4().hex[:8].upper()}"
        appointment_id = str(uuid.uuid4())

        # TODO: Implement actual database insertion

        return {
            "success": True,
            "appointment_id": appointment_id,
            "confirmation_code": confirmation_code,
            "date": date_str,
            "time": time_str,
        }

    @agent.tool
    async def cancel_appointment(
        ctx: RunContext[AgentDependencies],
        confirmation_code: str,
    ) -> dict[str, Any]:
        """Cancela um agendamento existente.

        Args:
            ctx: Run context with dependencies.
            confirmation_code: Código de confirmação do agendamento.

        Returns:
            Dict com 'success' e 'message'.
        """
        logger.info(
            "cancel_appointment",
            trace_id=ctx.deps.trace_id,
            confirmation_code=confirmation_code,
        )

        # TODO: Implement actual cancellation with database

        return {
            "success": True,
            "message": f"Agendamento {confirmation_code} cancelado com sucesso.",
        }

    return agent


# Global agent instance (lazy initialization)
_agent: Agent[AgentDependencies, dict[str, Any]] | None = None


def get_agent() -> Agent[AgentDependencies, dict[str, Any]]:
    """Get or create the global agent instance.

    Returns:
        Agent instance.
    """
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


async def process_message(message: WhatsAppMessage) -> AgentResponse:
    """Process incoming WhatsApp message and return agent response.

    This is the main entry point for message processing.

    Args:
        message: Validated WhatsApp message.

    Returns:
        AgentResponse with intent, reply, and extracted data.
    """
    trace_id = str(uuid.uuid4())

    logger.info(
        "process_message_start",
        trace_id=trace_id,
        message_id=message.message_id,
        from_number=message.from_number,
    )

    start_time = datetime.now()

    try:
        # Create dependencies
        deps = AgentDependencies(
            customer_id=message.from_number,
            trace_id=trace_id,
        )

        # Get agent and run
        agent = get_agent()
        result = await agent.run(message.body, deps=deps)

        # Parse result
        response_data = result.data if isinstance(result.data, dict) else {}

        # Determine intent from response
        intent_str = response_data.get("intent", "unknown")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            intent = IntentType.UNKNOWN

        # Build response
        response = AgentResponse(
            trace_id=trace_id,
            intent=intent,
            reply_text=response_data.get("reply", str(result.data)),
            confidence=response_data.get("confidence", 0.8),
            appointment_id=response_data.get("appointment_id"),
            extracted_data=response_data.get("extracted_data", {}),
            clarification_needed=response_data.get("clarification_needed", False),
        )

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "process_message_complete",
            trace_id=trace_id,
            intent=response.intent.value,
            confidence=response.confidence,
            latency_ms=elapsed_ms,
        )

        return response

    except Exception as e:
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.error(
            "process_message_error",
            trace_id=trace_id,
            error=str(e),
            error_type=type(e).__name__,
            latency_ms=elapsed_ms,
        )

        # Return error response
        return AgentResponse(
            trace_id=trace_id,
            intent=IntentType.UNKNOWN,
            reply_text="Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
            confidence=0.0,
            clarification_needed=True,
        )
