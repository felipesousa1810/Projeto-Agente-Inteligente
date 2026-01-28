"""WhatsApp Message Contract - Input validation for Evolution API webhook."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WhatsAppMessage(BaseModel):
    """Contrato de entrada: webhook Evolution API.

    Valida mensagens recebidas do WhatsApp via Evolution API,
    garantindo idempotência e type safety.
    """

    message_id: str = Field(
        ...,
        description="ID único para idempotência",
        min_length=16,
        max_length=64,
    )
    from_number: str = Field(
        ...,
        description="Telefone com código país",
        pattern=r"^\+?[1-9]\d{1,14}$",
    )
    body: str = Field(
        ...,
        description="Texto da mensagem",
        min_length=1,
        max_length=4096,
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp da mensagem",
    )

    @field_validator("body")
    @classmethod
    def sanitize_body(cls, v: str) -> str:
        """Remove caracteres não-textuais e espaços extras."""
        return v.strip()

    @field_validator("from_number")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        """Normaliza número de telefone para formato E.164."""
        # Remove espaços e caracteres especiais (exceto +)
        cleaned = "".join(c for c in v if c.isdigit() or c == "+")
        # Adiciona + se não tiver
        if not cleaned.startswith("+"):
            cleaned = f"+{cleaned}"
        return cleaned

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "message_id": "3EB0E51D3B4B1A25AA4AA001",
                "from_number": "+5511987654321",
                "body": "Quero agendar para 15 de fevereiro",
                "timestamp": "2026-01-28T10:30:45.123Z",
            }
        }
