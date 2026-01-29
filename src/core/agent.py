"""Pydantic AI Agent - Deterministic scheduling agent for OdontoSorriso clinic."""

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.config.agent_config import AgentConfig
from src.contracts.agent_response import AgentResponse, IntentType
from src.contracts.structured_output import StructuredAgentOutput
from src.contracts.whatsapp_message import WhatsAppMessage
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Mapping from structured output intent to IntentType enum
INTENT_MAPPING: dict[str, IntentType] = {
    "faq": IntentType.FAQ,
    "schedule": IntentType.SCHEDULE,
    "reschedule": IntentType.RESCHEDULE,
    "cancel": IntentType.CANCEL,
    "confirm": IntentType.CONFIRM,
    "greeting": IntentType.UNKNOWN,  # Map greeting to UNKNOWN for now
    "unknown": IntentType.UNKNOWN,
}


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
) -> Agent[AgentDependencies, StructuredAgentOutput]:
    """Create and configure the Pydantic AI agent.

    Args:
        config: Optional agent configuration. Uses defaults if not provided.

    Returns:
        Configured Agent instance with structured output.
    """
    if config is None:
        config = AgentConfig()

    # Create OpenAI model with deterministic settings
    model = OpenAIModel(
        config.model,
        # api_key is automatically loaded from OPENAI_API_KEY env var
    )

    # Create agent with structured output type
    agent: Agent[AgentDependencies, StructuredAgentOutput] = Agent(
        model=model,
        system_prompt=config.system_prompt,
        deps_type=AgentDependencies,
        output_type=StructuredAgentOutput,
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
_agent: Agent[AgentDependencies, StructuredAgentOutput] | None = None


def get_agent() -> Agent[AgentDependencies, StructuredAgentOutput]:
    """Get or create the global agent instance.

    Returns:
        Agent instance with structured output.
    """
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


async def process_message(message: WhatsAppMessage) -> AgentResponse:
    """Process incoming WhatsApp message and return agent response.

    This is the main entry point for message processing.
    Now with conversation context memory via FSM stored in Redis.

    Args:
        message: Validated WhatsApp message.

    Returns:
        AgentResponse with intent, reply, and extracted data.
    """
    from src.services.conversation_state import get_conversation_state_manager

    trace_id = str(uuid.uuid4())

    logger.info(
        "process_message_start",
        trace_id=trace_id,
        message_id=message.message_id,
        from_number=message.from_number,
    )

    start_time = datetime.now()

    try:
        # 1. Recuperar estado da conversa do Redis
        state_manager = get_conversation_state_manager()
        fsm = await state_manager.get_or_create(message.from_number)

        # 2. Construir contexto para o agente
        context = state_manager.build_context_prompt(fsm)

        # Combinar contexto com mensagem do usuário
        if context:
            prompt_with_context = (
                f"{context}\n\n**Mensagem do paciente:** {message.body}"
            )
        else:
            prompt_with_context = message.body

        logger.info(
            "process_message_with_context",
            trace_id=trace_id,
            has_context=bool(context),
            collected_data=fsm.collected_data,
        )

        # Create dependencies
        deps = AgentDependencies(
            customer_id=message.from_number,
            trace_id=trace_id,
        )

        # Get agent and run with context
        agent = get_agent()
        result = await agent.run(prompt_with_context, deps=deps)

        # Parse structured output from Pydantic AI
        output: StructuredAgentOutput = result.output

        # Map structured intent to IntentType enum
        intent = INTENT_MAPPING.get(output.intent, IntentType.UNKNOWN)

        # 3. Atualizar FSM com dados extraídos
        if output.extracted_date:
            fsm.set_data("date", output.extracted_date)
        if output.extracted_time:
            fsm.set_data("time", output.extracted_time)

        # Detectar procedimento da mensagem (heurística simples)
        body_lower = message.body.lower()
        procedures = [
            "limpeza",
            "clareamento",
            "restauração",
            "ortodontia",
            "implante",
            "prótese",
            "canal",
            "extração",
            "emergência",
            "consulta",
        ]
        for proc in procedures:
            if proc in body_lower and "procedure" not in fsm.collected_data:
                fsm.set_data("procedure", proc.title())
                break

        # 4. Salvar estado atualizado no Redis
        await state_manager.save(message.from_number, fsm)

        # Build extracted_data from structured output + FSM
        extracted_data: dict[str, str] = dict(fsm.collected_data)
        if output.extracted_date:
            extracted_data["date"] = output.extracted_date
        if output.extracted_time:
            extracted_data["time"] = output.extracted_time

        # Build response from structured output
        response = AgentResponse(
            trace_id=trace_id,
            intent=intent,
            reply_text=output.reply_text or "Não consegui processar sua mensagem.",
            confidence=output.confidence,
            appointment_id=None,
            extracted_data=extracted_data,
            clarification_needed=output.clarification_needed,
        )

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "process_message_complete",
            trace_id=trace_id,
            intent=response.intent.value,
            confidence=response.confidence,
            latency_ms=elapsed_ms,
            extracted_data=extracted_data,
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
