"""Pydantic AI Agent - Deterministic scheduling agent for OdontoSorriso clinic."""

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.config.agent_config import AgentConfig, get_dynamic_system_prompt
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
    "deny": IntentType.DENY,
    "greeting": IntentType.GREETING,
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

    # Get dynamic system prompt with current date/time
    dynamic_prompt = get_dynamic_system_prompt()

    # Create agent with structured output type
    agent: Agent[AgentDependencies, StructuredAgentOutput] = Agent(
        model=model,
        system_prompt=dynamic_prompt,
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
    """Process incoming WhatsApp message using DETERMINISTIC architecture.

    Architecture: NLU → DecisionEngine → Templates → NLG
    - NLU: Extracts intent and entities (LLM)
    - DecisionEngine: Decides next action (CODE - 100% deterministic)
    - Templates: Provides response structure (CODE)
    - NLG: Humanizes the response (LLM)

    Args:
        message: Validated WhatsApp message.

    Returns:
        AgentResponse with intent, reply, and extracted data.
    """
    from src.core.decision_engine import get_decision_engine
    from src.core.nlg import NLG
    from src.core.nlu import NLU
    from src.core.templates import format_template, get_faq_answer
    from src.services.conversation_state import get_conversation_state_manager

    trace_id = str(uuid.uuid4())
    now = datetime.now()

    logger.info(
        "process_message_start",
        trace_id=trace_id,
        message_id=message.message_id,
        from_number=message.from_number,
        architecture="deterministic",
    )

    start_time = now

    try:
        # =====================================================
        # STEP 1: Get conversation state from Redis
        # =====================================================
        state_manager = get_conversation_state_manager()
        fsm = await state_manager.get_or_create(message.from_number)

        logger.info(
            "fsm_state_loaded",
            trace_id=trace_id,
            current_state=fsm.current_state.value,
            collected_data=fsm.collected_data,
        )

        # =====================================================
        # STEP 2: NLU - Extract intent and entities (LLM)
        # =====================================================
        nlu = NLU()
        nlu_output = await nlu.extract(
            message=message.body,
            current_date=now.strftime("%Y-%m-%d"),
            current_time=now.strftime("%H:%M"),
        )

        logger.info(
            "nlu_extraction_complete",
            trace_id=trace_id,
            intent=nlu_output.intent,
            extracted_date=nlu_output.extracted_date,
            extracted_time=nlu_output.extracted_time,
            extracted_procedure=nlu_output.extracted_procedure,
            confidence=nlu_output.confidence,
        )

        # =====================================================
        # STEP 3: DecisionEngine - Decide next action (CODE)
        # This is 100% DETERMINISTIC - same input = same output
        # =====================================================
        decision_engine = get_decision_engine()
        action = decision_engine.decide(fsm, nlu_output)

        logger.info(
            "decision_made",
            trace_id=trace_id,
            action_type=action.action_type.value,
            template_key=action.template_key,
            requires_tool=action.requires_tool,
        )

        # =====================================================
        # STEP 4: Execute tool if needed (CODE)
        # =====================================================
        tool_result: dict[str, Any] = {}
        if action.requires_tool and action.tool_name:
            tool_result = await _execute_tool(
                action.tool_name,
                action.context,
                message.from_number,
                trace_id,
            )
            # Merge tool result into context
            action.context.update(tool_result)

        # =====================================================
        # STEP 5: Format template (CODE)
        # =====================================================
        # Handle special cases
        if action.template_key == "faq_response":
            faq_answer = get_faq_answer(nlu_output.extracted_procedure)
            action.context["answer"] = faq_answer
            if not nlu_output.extracted_procedure:
                action.context["procedure"] = "tratamentos"

        # Handle availability for time slots
        if action.template_key == "ask_time":
            slots = action.context.get(
                "available_slots", "09:00, 10:00, 14:00, 15:00, 16:00"
            )
            if isinstance(slots, list):
                slots = ", ".join(slots)
            action.context["available_slots"] = slots

        template_text = format_template(action.template_key, **action.context)

        logger.info(
            "template_formatted",
            trace_id=trace_id,
            template_key=action.template_key,
            template_length=len(template_text),
        )

        # =====================================================
        # STEP 6: NLG - Humanize response (LLM)
        # =====================================================
        nlg = NLG(skip_humanization=False)  # Set to True for faster responses
        humanized_response = await nlg.humanize(template_text)

        # =====================================================
        # STEP 7: Update FSM state if action specifies
        # =====================================================
        if action.next_state and fsm.can_transition_to(action.next_state):
            fsm.transition(action.next_state)

        # Save updated FSM to Redis
        await state_manager.save(message.from_number, fsm)

        # =====================================================
        # STEP 8: Build and return response
        # =====================================================
        # Map NLU intent to IntentType enum
        intent = INTENT_MAPPING.get(nlu_output.intent, IntentType.UNKNOWN)

        # Build extracted_data from FSM
        extracted_data: dict[str, str] = dict(fsm.collected_data)

        response = AgentResponse(
            trace_id=trace_id,
            intent=intent,
            reply_text=humanized_response,
            confidence=nlu_output.confidence,
            appointment_id=tool_result.get("appointment_id"),
            extracted_data=extracted_data,
            clarification_needed=action.action_type.value == "clarify",
        )

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "process_message_complete",
            trace_id=trace_id,
            intent=response.intent.value,
            confidence=response.confidence,
            latency_ms=elapsed_ms,
            extracted_data=extracted_data,
            architecture="deterministic",
        )

        return response

    except Exception as e:
        import traceback

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.error(
            "process_message_error",
            trace_id=trace_id,
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
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


async def _execute_tool(
    tool_name: str,
    context: dict[str, Any],
    customer_id: str,
    trace_id: str,
) -> dict[str, Any]:
    """Execute a tool based on action requirements.

    Args:
        tool_name: Name of the tool to execute.
        context: Context data for the tool.
        customer_id: Customer phone number.
        trace_id: Trace ID for logging.

    Returns:
        Tool execution result.
    """
    logger.info(
        "tool_execution_start",
        trace_id=trace_id,
        tool_name=tool_name,
    )

    if tool_name == "check_availability":
        # TODO: Use context.get("date") for real availability check
        # Return mock availability for now
        return {
            "available": True,
            "available_slots": ["09:00", "10:00", "14:00", "15:00", "16:00"],
        }

    if tool_name == "create_appointment":
        # Generate confirmation code
        confirmation_code = f"APPT-{uuid.uuid4().hex[:8].upper()}"
        appointment_id = str(uuid.uuid4())

        # TODO: Implement actual database insertion

        return {
            "success": True,
            "appointment_id": appointment_id,
            "confirmation_code": confirmation_code,
        }

    if tool_name == "cancel_appointment":
        confirmation_code = context.get("confirmation_code", "")
        # TODO: Implement actual cancellation

        return {
            "success": True,
            "message": f"Agendamento {confirmation_code} cancelado.",
        }

    logger.warning(
        "unknown_tool",
        trace_id=trace_id,
        tool_name=tool_name,
    )
    return {}
