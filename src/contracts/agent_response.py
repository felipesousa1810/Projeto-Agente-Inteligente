"""Agent Response Contract - Output validation for agent responses."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class IntentType(str, Enum):
    """Tipos de intenção detectadas pelo agente."""

    FAQ = "faq"
    SCHEDULE = "schedule"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    CONFIRM = "confirm"
    DENY = "deny"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class AgentResponse(BaseModel):
    """Contrato de saída: resposta do agente.

    Define a estrutura padronizada de resposta do agente,
    incluindo rastreabilidade e métricas de confiança.
    """

    trace_id: str = Field(
        ...,
        description="UUID para rastreamento",
    )
    intent: IntentType = Field(
        ...,
        description="Intenção detectada",
    )
    reply_text: str = Field(
        ...,
        description="Texto da resposta para o usuário",
        min_length=1,
        max_length=4096,
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score de confiança da classificação",
    )
    appointment_id: str | None = Field(
        None,
        description="ID do agendamento (se aplicável)",
    )
    extracted_data: dict[str, str] = Field(
        default_factory=dict,
        description="Dados extraídos da mensagem (data, hora, etc)",
    )
    clarification_needed: bool = Field(
        False,
        description="Se o agente precisa de mais informações",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "intent": "schedule",
                "reply_text": "Perfeito! Agendei sua consulta para 15/02/2026 às 14:00.",
                "confidence": 0.95,
                "appointment_id": "appt_123456",
                "extracted_data": {"date": "2026-02-15", "time": "14:00"},
                "clarification_needed": False,
            }
        }
    )
