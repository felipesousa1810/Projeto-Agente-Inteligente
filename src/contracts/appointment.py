"""Appointment Contract - Models for appointment management."""

from datetime import date, datetime, time
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AppointmentStatus(str, Enum):
    """Status possíveis de um agendamento."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"


class AppointmentCreate(BaseModel):
    """Schema para criação de agendamento."""

    customer_id: UUID = Field(
        ...,
        description="ID do cliente",
    )
    scheduled_date: date = Field(
        ...,
        description="Data do agendamento",
    )
    scheduled_time: time = Field(
        ...,
        description="Hora do agendamento",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "scheduled_date": "2026-02-15",
                "scheduled_time": "14:00:00",
            }
        }
    )


class Appointment(BaseModel):
    """Schema completo de agendamento (leitura do DB)."""

    id: UUID = Field(
        ...,
        description="ID único do agendamento",
    )
    customer_id: UUID = Field(
        ...,
        description="ID do cliente",
    )
    scheduled_date: date = Field(
        ...,
        description="Data do agendamento",
    )
    scheduled_time: time = Field(
        ...,
        description="Hora do agendamento",
    )
    status: AppointmentStatus = Field(
        ...,
        description="Status atual",
    )
    confirmation_code: str = Field(
        ...,
        description="Código de confirmação único",
    )
    created_at: datetime = Field(
        ...,
        description="Data de criação",
    )
    updated_at: datetime = Field(
        ...,
        description="Data de atualização",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "customer_id": "660e8400-e29b-41d4-a716-446655440001",
                "scheduled_date": "2026-02-15",
                "scheduled_time": "14:00:00",
                "status": "scheduled",
                "confirmation_code": "APPT-ABC123",
                "created_at": "2026-01-28T10:00:00Z",
                "updated_at": "2026-01-28T10:00:00Z",
            }
        },
    )


class Customer(BaseModel):
    """Schema de cliente."""

    id: UUID = Field(
        ...,
        description="ID único do cliente",
    )
    phone_number: str = Field(
        ...,
        description="Número de telefone",
    )
    name: str | None = Field(
        None,
        description="Nome do cliente",
    )
    created_at: datetime = Field(
        ...,
        description="Data de criação",
    )
    updated_at: datetime = Field(
        ...,
        description="Data de atualização",
    )

    model_config = ConfigDict(from_attributes=True)
