"""Contracts package - Pydantic schemas for data validation."""

from src.contracts.agent_response import AgentResponse, IntentType
from src.contracts.appointment import Appointment, AppointmentCreate, AppointmentStatus
from src.contracts.whatsapp_message import WhatsAppMessage

__all__ = [
    "WhatsAppMessage",
    "AgentResponse",
    "IntentType",
    "Appointment",
    "AppointmentCreate",
    "AppointmentStatus",
]
