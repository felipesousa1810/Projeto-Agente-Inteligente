"""Structured Output Contract - LLM output validation.

Define o formato estruturado que o LLM deve retornar para garantir
detecção correta de intent e extração de dados.
"""

from typing import Literal

from pydantic import BaseModel, Field


class StructuredAgentOutput(BaseModel):
    """Output estruturado que o LLM deve retornar.

    Este modelo força o LLM a responder em formato JSON estruturado,
    garantindo detecção precisa de intent e extração de dados.
    """

    intent: Literal[
        "faq", "schedule", "reschedule", "cancel", "confirm", "greeting", "unknown"
    ] = Field(
        ...,
        description="Intenção detectada na mensagem do usuário",
    )
    reply_text: str = Field(
        ...,
        description="Texto da resposta para enviar ao usuário",
        min_length=1,
        max_length=2048,
    )
    extracted_date: str | None = Field(
        None,
        description="Data extraída no formato YYYY-MM-DD, se mencionada",
    )
    extracted_time: str | None = Field(
        None,
        description="Hora extraída no formato HH:MM, se mencionada",
    )
    clarification_needed: bool = Field(
        False,
        description="Se precisa de mais informações do usuário para prosseguir",
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confiança na classificação do intent (0.0 a 1.0)",
    )
