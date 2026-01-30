"""NLG (Natural Language Generation) - Humanize templates.

This module transforms base templates into natural, human-like responses.
It uses an LLM but with strict constraints:
- Data in the template CANNOT be changed
- Only style and phrasing can be adjusted
- The meaning must remain identical

Architecture principle: Templates provide structure, NLG adds warmth.
"""

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits

from src.utils.logger import get_logger

logger = get_logger(__name__)


class NLGOutput(BaseModel):
    """Structured output from NLG.

    Contains the humanized text that maintains all original data.
    """

    humanized_text: str = Field(
        ...,
        description="The humanized version of the template. Must contain ALL original data.",
        min_length=1,
        max_length=2048,
    )


# NLG system prompt - strict about preserving data
NLG_SYSTEM_PROMPT = """Você é um assistente de linguagem natural para uma clínica odontológica.

Sua ÚNICA tarefa é humanizar mensagens, tornando-as mais naturais e amigáveis.

REGRAS CRÍTICAS:
1. NUNCA altere dados como datas, horários, códigos, nomes de procedimentos
2. NUNCA adicione informações que não estavam na mensagem original
3. NUNCA remova informações importantes
4. Mantenha um tom profissional mas acolhedor
5. Use emojis com moderação (já incluídos na maioria dos templates)
6. A mensagem humanizada deve ter aproximadamente o mesmo tamanho

EXEMPLOS:

Original: "Perfeito! Para o dia 15/02, temos os seguintes horários disponíveis: 09:00, 14:00, 16:00"
Humanizado: "Ótimo! No dia 15/02 temos três opções de horário: 09:00, 14:00 e 16:00. Qual fica melhor pra você?"

Original: "Agendamento confirmado! Procedimento: Limpeza, Data: 15/02, Horário: 14:00"
Humanizado: "Tudo certo! ✨ Sua limpeza está agendada para o dia 15/02 às 14:00. Te esperamos!"

Quando a mensagem já está boa, retorne-a com pequenos ajustes ou igual.
"""


def _create_nlg_agent() -> Agent[None, NLGOutput]:
    """Create the NLG agent."""
    model = OpenAIModel("gpt-4.1-mini-2025-04-14")

    agent: Agent[None, NLGOutput] = Agent(
        model=model,
        output_type=NLGOutput,
        system_prompt=NLG_SYSTEM_PROMPT,
        retries=1,
    )

    return agent


# Singleton NLG agent
_nlg_agent: Agent[None, NLGOutput] | None = None


def get_nlg_agent() -> Agent[None, NLGOutput]:
    """Get or create the NLG agent singleton."""
    global _nlg_agent
    if _nlg_agent is None:
        _nlg_agent = _create_nlg_agent()
    return _nlg_agent


class NLG:
    """Natural Language Generation - humanizes templates.

    Takes structured templates and makes them feel more natural
    while preserving all data.
    """

    def __init__(self, skip_humanization: bool = False) -> None:
        """Initialize NLG.

        Args:
            skip_humanization: If True, skip LLM and return template as-is.
                             Useful for testing or low-latency requirements.
        """
        self.agent = get_nlg_agent()
        self.skip_humanization = skip_humanization

    async def humanize(self, template_text: str) -> str:
        """Humanize a template text.

        Args:
            template_text: The filled template to humanize.

        Returns:
            Humanized version of the text.
        """
        # Skip humanization if disabled
        if self.skip_humanization:
            return template_text

        # Very short messages don't need humanization
        if len(template_text) < 50:
            return template_text

        logger.info(
            "nlg_humanize_start",
            text_length=len(template_text),
        )

        try:
            result = await self.agent.run(
                f"Humanize esta mensagem mantendo TODOS os dados:\n\n{template_text}",
                usage_limits=UsageLimits(
                    request_limit=2,  # Max 2 attempts
                    total_tokens_limit=1024,  # Keep it fast
                ),
            )

            humanized = result.data.humanized_text

            logger.info(
                "nlg_humanize_complete",
                original_length=len(template_text),
                humanized_length=len(humanized),
            )

            return humanized

        except Exception as e:
            logger.error(
                "nlg_humanize_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            # On error, return original template
            return template_text


# Convenience function
async def humanize_response(template_text: str, skip: bool = False) -> str:
    """Convenience function to humanize a response.

    Args:
        template_text: Text to humanize.
        skip: Whether to skip humanization.

    Returns:
        Humanized text.
    """
    nlg = NLG(skip_humanization=skip)
    return await nlg.humanize(template_text)
