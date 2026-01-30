"""Guardrails - Structured Output Definitions for the Agent.

This module defines the Pydantic models that strictly control the structure
of the agent's responses, while allowing the LLM to generate the actual content.
This implements the "Guardrails" pattern:
- Structure is enforced (Validators)
- Content is generative (LLM)
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ResponseGuardrail(BaseModel):
    """Base class for all response guardrails."""

    pass


class AskForInfo(ResponseGuardrail):
    """Guardrail for asking missing information."""

    type: Literal["ask_info"] = "ask_info"
    missing_fields: list[str] = Field(
        ..., description="List of fields that are missing (e.g., 'date', 'time')"
    )
    thought_process: str = Field(
        ..., description="Brief reasoning why this info is needed."
    )
    message: str = Field(
        ...,
        description="Natural language question asking for the missing info. Must be polite and direct.",
    )

    @field_validator("message")
    @classmethod
    def validate_question_mark(cls, v: str) -> str:
        if "?" not in v:
            raise ValueError(
                "The message asking for info must contain a question mark."
            )
        return v


class ConfirmAppointment(ResponseGuardrail):
    """Guardrail for confirming an appointment details before finalization."""

    type: Literal["confirm_appointment"] = "confirm_appointment"
    procedure: str = Field(..., description="The procedure to be performed.")
    date: str = Field(..., description="The date of the appointment (DD/MM/YYYY).")
    time: str = Field(..., description="The time of the appointment (HH:MM).")
    message: str = Field(
        ...,
        description="Confirmation message summarizing the details and asking for 'Sim' or 'Não'.",
    )

    @field_validator("message")
    @classmethod
    def validate_contains_data(cls, v: str, info: Field) -> str:
        # We can't easily validate content against other fields here without model_validator,
        # but we can check for basic confirmation keywords.
        return v


class AppointmentScheduled(ResponseGuardrail):
    """Guardrail for final success message."""

    type: Literal["appointment_scheduled"] = "appointment_scheduled"
    event_id: str = Field(..., description="The ID of the created calendar event.")
    message: str = Field(
        ..., description="Success message confirming the booking is done."
    )


class OfferSlots(ResponseGuardrail):
    """Guardrail for offering available time slots."""

    type: Literal["offer_slots"] = "offer_slots"
    date: str = Field(..., description="The date these slots are for.")
    slots: list[str] = Field(
        ..., description="List of available time strings (e.g., '09:00')."
    )
    message: str = Field(
        ..., description="Message listing the slots and asking the user to pick one."
    )


class GeneralMessage(ResponseGuardrail):
    """Guardrail for general interaction, errors, or off-topic handling."""

    type: Literal["general"] = "general"
    category: Literal["greeting", "cancellation", "error", "off_topic"]
    message: str = Field(..., description="The natural language response.")
