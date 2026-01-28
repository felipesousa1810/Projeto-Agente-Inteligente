"""WhatsApp Message Contract - Input validation for Evolution API webhook."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class EvolutionKey(BaseModel):
    """Event key info."""

    remoteJid: str
    fromMe: bool
    id: str


class EvolutionMessageContent(BaseModel):
    """Message content (supports conversation and extendedTextMessage)."""

    conversation: str | None = None
    extendedTextMessage: dict[str, Any] | None = None

    def get_text(self) -> str:
        """Extract text from message."""
        if self.conversation:
            return self.conversation
        if self.extendedTextMessage and "text" in self.extendedTextMessage:
            return str(self.extendedTextMessage["text"])
        return ""


class EvolutionData(BaseModel):
    """Evolution webhook data."""

    key: EvolutionKey
    pushName: str | None = None
    message: EvolutionMessageContent | None = None
    messageTimestamp: int | datetime

    @field_validator("messageTimestamp")
    @classmethod
    def validate_timestamp(cls, v: Any) -> datetime:
        """Convert timestamp to datetime if needed."""
        if isinstance(v, int):
            return datetime.fromtimestamp(v)
        return v


class EvolutionWebhook(BaseModel):
    """Evolution API Webhook Payload."""

    event: str
    instance: str | None = None
    data: EvolutionData
    sender: str | None = None


class WhatsAppMessage(BaseModel):
    """Internal Contract: Normalized WhatsApp Message."""

    message_id: str = Field(..., min_length=4)
    from_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    body: str = Field(..., min_length=1)
    timestamp: datetime
    push_name: str | None = None

    @classmethod
    def from_evolution(cls, payload: EvolutionWebhook) -> "WhatsAppMessage | None":
        """Convert Evolution payload to internal message.

        Returns None if:
        - Message is from me (fromMe=True)
        - Message has no text body
        - Not a messages.upsert event
        """
        # 1. Filter events
        if payload.event != "messages.upsert":
            return None

        data = payload.data

        # 2. Filter outgoing messages
        if data.key.fromMe:
            return None

        # 3. Extract body
        body = ""
        if data.message:
            body = data.message.get_text()

        if not body:
            return None

        # 4. Extract phone number
        remote_jid = data.key.remoteJid
        phone = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid

        return cls(
            message_id=data.key.id,
            from_number=phone,
            body=body,
            timestamp=data.messageTimestamp,
            push_name=data.pushName,
        )

    @field_validator("body")
    @classmethod
    def sanitize_body(cls, v: str) -> str:
        """Remove empty space."""
        return v.strip()

    @field_validator("from_number")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        """Normalize to E.164."""
        cleaned = "".join(c for c in v if c.isdigit() or c == "+")
        if not cleaned.startswith("+"):
            cleaned = f"+{cleaned}"
        return cleaned
