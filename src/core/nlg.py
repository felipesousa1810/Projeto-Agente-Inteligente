"""NLG (Natural Language Generation) - Guardrails Architecture.

This module is responsible for generating natural language responses that STRICTLY
adhere to the structural constraints defined in `src/core/guardrails.py`.

Architecture:
1. Input: Action (from Decision Engine) + Context
2. Process: LLM generates content fitting the specific Guardrail Pydantic model
3. Output: Validated, structured response (JSON) -> Converted to text for user
"""

from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from src.config.settings import get_settings
from src.core.decision_engine import Action, ActionType
from src.core.guardrails import (
    AppointmentScheduled,
    AskForInfo,
    ConfirmAppointment,
    GeneralMessage,
    OfferSlots,
    ResponseGuardrail,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ResponseSystemPrompt:
    """System prompts for the NLG Agent."""

    BASE = """Você é a Ana, assistente virtual da Clínica Odontológica.
Sua persona: Profissional, acolhedora, eficiente e direta.
NUNCA invente informações. Use apenas o contexto fornecido.
Seu objetivo é gerar a resposta para o usuário seguindo ESTRITAMENTE o schema solicitado."""


def _get_model_for_action(action_type: ActionType) -> type[BaseModel]:
    """Map ActionType to the specific Guardrail Pydantic Model."""
    match action_type:
        case (
            ActionType.ASK_PROCEDURE
            | ActionType.ASK_DATE
            | ActionType.ASK_TIME
            | ActionType.ASK_CONFIRMATION_CODE
        ):
            return AskForInfo
        case ActionType.CONFIRM_APPOINTMENT:
            return ConfirmAppointment
        case ActionType.APPOINTMENT_CONFIRMED:
            return AppointmentScheduled
        case ActionType.CHECK_AVAILABILITY:  # Assuming this action might result in offering slots
            return OfferSlots
        case _:
            return GeneralMessage


class ResponseGenerator:
    """Generates responses using PydanticAI Guardrails."""

    def __init__(self):
        settings = get_settings()
        model = OpenAIModel(
            "gpt-4o-mini",  # Use a smart model for accurate structure following
            api_key=settings.openai_api_key,
        )

        self.agent = Agent(
            model=model, system_prompt=ResponseSystemPrompt.BASE, retries=2
        )

    async def generate(
        self, action: Action, context: dict[str, Any]
    ) -> ResponseGuardrail:
        """Generate a validated response for the given action."""

        target_model = _get_model_for_action(action.action_type)

        logger.info(
            "nlg_generate_start",
            action_type=action.action_type,
            target_model=target_model.__name__,
        )

        prompt = (
            f"Ação do Sistema: {action.action_type}\n"
            f"Contexto Disponível: {context}\n"
            f"Tarefa: Gere uma resposta para o usuário que se encaixe no modelo {target_model.__name__}."
        )

        # Special handling for specific contexts to guide the LLM
        if action.action_type == ActionType.ASK_TIME:
            prompt += "\nPergunte o horário preferido para o agendamento."
        elif action.action_type == ActionType.ASK_DATE:
            prompt += "\nPergunte a data preferida para o agendamento."

        try:
            result = await self.agent.run(
                prompt,
                result_type=target_model,  # Enforces the Guardrail!
            )

            response = result.output

            logger.info(
                "nlg_generate_success",
                response_type=type(response).__name__,
                message_preview=response.message[:50],
            )

            return response

        except Exception as e:
            logger.error("nlg_generate_error", error=str(e))
            # Fallback for critical failures
            return GeneralMessage(
                category="error",
                message="Desculpe, tive um problema técnico. Pode repetir?",
            )


# Singleton
_response_generator = None


def get_response_generator() -> ResponseGenerator:
    global _response_generator
    if _response_generator is None:
        _response_generator = ResponseGenerator()
    return _response_generator


async def generate_response(action: Action) -> str:
    """Convenience function to generate just the text message."""
    generator = get_response_generator()
    response = await generator.generate(action, action.context)
    return response.message
