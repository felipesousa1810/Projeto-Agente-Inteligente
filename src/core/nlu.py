"""NLU (Natural Language Understanding) - Extract intent and entities only.

This module is responsible ONLY for extracting intent and entities from user messages.
It does NOT decide what action to take - that's the Decision Engine's job.

Architecture principle: LLM extracts, Code decides.
"""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits

from src.utils.logger import get_logger

logger = get_logger(__name__)


# Valid intents the system can handle
IntentType = Literal[
    "schedule",  # User wants to schedule an appointment
    "reschedule",  # User wants to change existing appointment
    "cancel",  # User wants to cancel appointment
    "confirm",  # User is confirming something (yes, ok, etc)
    "deny",  # User is denying something (no, cancel, etc)
    "faq",  # User is asking a question about services
    "greeting",  # User is greeting (olá, oi, etc)
    "unknown",  # Cannot determine intent
]


class NLUOutput(BaseModel):
    """Structured output from NLU - extraction only, no decisions.

    This model is validated by Pydantic AI automatically.
    The LLM fills this structure, code decides what to do with it.
    """

    intent: IntentType = Field(
        ...,
        description="The detected intent from the user message",
    )
    extracted_date: str | None = Field(
        None,
        description="Date extracted in YYYY-MM-DD format, if mentioned",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    extracted_time: str | None = Field(
        None,
        description="Time extracted in HH:MM format (24h), if mentioned",
        pattern=r"^\d{2}:\d{2}$",
    )
    extracted_procedure: str | None = Field(
        None,
        description="Dental procedure mentioned (limpeza, clareamento, etc)",
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the intent classification",
    )


# NLU-specific system prompt - focused only on extraction
NLU_SYSTEM_PROMPT = """Você é um extrator de intenções para uma clínica odontológica.

Sua ÚNICA tarefa é extrair informações da mensagem do usuário:
1. **intent**: Qual é a intenção do usuário?
2. **extracted_date**: Se mencionou uma data, extraia no formato YYYY-MM-DD
3. **extracted_time**: Se mencionou um horário, extraia no formato HH:MM
4. **extracted_procedure**: Se mencionou um procedimento odontológico

REGRAS IMPORTANTES:
- Você NÃO responde ao usuário
- Você NÃO decide o que fazer
- Você APENAS extrai informações estruturadas
- Se não conseguir determinar algo, deixe como null/unknown
- Para datas relativas como "amanhã" ou "próxima semana", calcule a data real

INTENTS DISPONÍVEIS:
- schedule: Quer agendar (Ex: "quero marcar", "preciso agendar")
- reschedule: Quer remarcar (Ex: "preciso mudar a data", "remarcar")
- cancel: Quer cancelar (Ex: "cancelar consulta", "não posso ir")
- confirm: Está confirmando (Ex: "sim", "ok", "pode ser", "confirmo")
- deny: Está negando (Ex: "não", "cancelar", "não quero")
- faq: Pergunta sobre serviços (Ex: "quanto custa", "vocês fazem")
- greeting: Saudação (Ex: "olá", "oi", "bom dia")
- unknown: Não conseguiu determinar

PROCEDIMENTOS CONHECIDOS:
- Limpeza, Clareamento, Restauração, Ortodontia, Implante
- Prótese, Canal, Extração, Consulta, Avaliação
"""


def _create_nlu_agent() -> Agent[None, NLUOutput]:
    """Create the NLU agent with structured output."""
    model = OpenAIModel("gpt-4.1-mini-2025-04-14")

    agent: Agent[None, NLUOutput] = Agent(
        model=model,
        output_type=NLUOutput,
        system_prompt=NLU_SYSTEM_PROMPT,
        retries=1,  # One retry on validation failure
    )

    return agent


# Singleton NLU agent
_nlu_agent: Agent[None, NLUOutput] | None = None


def get_nlu_agent() -> Agent[None, NLUOutput]:
    """Get or create the NLU agent singleton."""
    global _nlu_agent
    if _nlu_agent is None:
        _nlu_agent = _create_nlu_agent()
    return _nlu_agent


class NLU:
    """Natural Language Understanding - extracts intent and entities.

    This class wraps the NLU agent and provides a clean interface
    for extracting structured information from user messages.
    """

    def __init__(self) -> None:
        """Initialize NLU with the shared agent."""
        self.agent = get_nlu_agent()

    async def extract(
        self,
        message: str,
        current_date: str | None = None,
        current_time: str | None = None,
    ) -> NLUOutput:
        """Extract intent and entities from a user message.

        Args:
            message: The user's message text.
            current_date: Current date in YYYY-MM-DD format for relative date resolution.
            current_time: Current time in HH:MM format.

        Returns:
            NLUOutput with extracted intent and entities.
        """
        # Build context prompt with current date/time for relative date resolution
        context_parts = []
        if current_date:
            context_parts.append(f"Data atual: {current_date}")
        if current_time:
            context_parts.append(f"Hora atual: {current_time}")

        prompt = message
        if context_parts:
            context = " | ".join(context_parts)
            prompt = f"[{context}] {message}"

        logger.info(
            "nlu_extract_start",
            message_preview=message[:50] if len(message) > 50 else message,
        )

        try:
            result = await self.agent.run(
                prompt,
                usage_limits=UsageLimits(
                    request_limit=3,  # Max 3 LLM requests for NLU
                    total_tokens_limit=1024,  # NLU should be fast
                ),
            )

            output = result.data

            logger.info(
                "nlu_extract_complete",
                intent=output.intent,
                has_date=output.extracted_date is not None,
                has_time=output.extracted_time is not None,
                has_procedure=output.extracted_procedure is not None,
                confidence=output.confidence,
            )

            return output

        except Exception as e:
            logger.error(
                "nlu_extract_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return unknown intent on error
            return NLUOutput(
                intent="unknown",
                confidence=0.0,
            )


# Convenience function for quick extraction
async def extract_intent(
    message: str,
    current_date: str | None = None,
    current_time: str | None = None,
) -> NLUOutput:
    """Convenience function to extract intent from a message.

    Args:
        message: User message to analyze.
        current_date: Current date for relative date resolution.
        current_time: Current time.

    Returns:
        NLUOutput with extracted data.
    """
    nlu = NLU()
    return await nlu.extract(message, current_date, current_time)
