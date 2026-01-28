"""Contract Tests - Validate Pydantic schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.contracts.agent_response import AgentResponse, IntentType
from src.contracts.appointment import Appointment, AppointmentCreate, AppointmentStatus
from src.contracts.whatsapp_message import WhatsAppMessage


class TestWhatsAppMessageContract:
    """Tests for WhatsAppMessage schema."""

    def test_valid_message(self, sample_whatsapp_message: dict) -> None:
        """Test that valid message passes validation."""
        msg = WhatsAppMessage(**sample_whatsapp_message)

        assert msg.message_id == sample_whatsapp_message["message_id"]
        assert msg.from_number == "+5511987654321"
        assert "agendar" in msg.body

    def test_message_body_stripped(self) -> None:
        """Test that message body is stripped of whitespace."""
        msg = WhatsAppMessage(
            message_id="MSG12345678901234567",
            from_number="+5511999999999",
            body="   Mensagem com espaços   ",
            timestamp=datetime.now(),
        )

        assert msg.body == "Mensagem com espaços"

    def test_phone_number_normalized(self) -> None:
        """Test that phone numbers are normalized."""
        msg = WhatsAppMessage(
            message_id="MSG12345678901234567",
            from_number="5511999999999",  # Without +
            body="Test message",
            timestamp=datetime.now(),
        )

        assert msg.from_number == "+5511999999999"

    def test_invalid_message_id_too_short(self) -> None:
        """Test that short message_id fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            WhatsAppMessage(
                message_id="abc",  # Too short (< 4)
                from_number="+5511999999999",
                body="Test",
                timestamp=datetime.now(),
            )

        assert "message_id" in str(exc_info.value)

    def test_invalid_phone_number(self) -> None:
        """Test that invalid phone number fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            WhatsAppMessage(
                message_id="MSG12345678901234567",
                from_number="invalid-phone",
                body="Test",
                timestamp=datetime.now(),
            )

        assert "from_number" in str(exc_info.value)

    def test_empty_body_fails(self) -> None:
        """Test that empty body fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            WhatsAppMessage(
                message_id="MSG12345678901234567",
                from_number="+5511999999999",
                body="",  # Empty
                timestamp=datetime.now(),
            )

        assert "body" in str(exc_info.value)


class TestAgentResponseContract:
    """Tests for AgentResponse schema."""

    def test_valid_response(self) -> None:
        """Test that valid response passes validation."""
        response = AgentResponse(
            trace_id="550e8400-e29b-41d4-a716-446655440000",
            intent=IntentType.SCHEDULE,
            reply_text="Agendamento confirmado para 15/02/2026 às 14:00.",
            confidence=0.95,
        )

        assert response.intent == IntentType.SCHEDULE
        assert response.confidence == 0.95

    def test_response_with_optional_fields(self) -> None:
        """Test response with all optional fields."""
        response = AgentResponse(
            trace_id="test-trace-id",
            intent=IntentType.SCHEDULE,
            reply_text="Confirmado!",
            confidence=0.9,
            appointment_id="appt_123",
            extracted_data={"date": "2026-02-15", "time": "14:00"},
            clarification_needed=False,
        )

        assert response.appointment_id == "appt_123"
        assert response.extracted_data["date"] == "2026-02-15"

    def test_confidence_out_of_range(self) -> None:
        """Test that confidence out of range fails."""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                trace_id="test-trace",
                intent=IntentType.UNKNOWN,
                reply_text="Test",
                confidence=1.5,  # > 1.0
            )

        assert "confidence" in str(exc_info.value)

    def test_intent_enum_values(self) -> None:
        """Test all intent enum values."""
        intents = [
            IntentType.FAQ,
            IntentType.SCHEDULE,
            IntentType.RESCHEDULE,
            IntentType.CANCEL,
            IntentType.CONFIRM,
            IntentType.UNKNOWN,
        ]

        for intent in intents:
            response = AgentResponse(
                trace_id="test",
                intent=intent,
                reply_text="Test response",
                confidence=0.8,
            )
            assert response.intent == intent


class TestAppointmentContract:
    """Tests for Appointment schemas."""

    def test_appointment_create_valid(self) -> None:
        """Test valid appointment creation."""
        from datetime import date, time
        from uuid import uuid4

        appt = AppointmentCreate(
            customer_id=uuid4(),
            scheduled_date=date(2026, 2, 15),
            scheduled_time=time(14, 0),
        )

        assert appt.scheduled_date.year == 2026
        assert appt.scheduled_time.hour == 14

    def test_appointment_status_enum(self) -> None:
        """Test appointment status values."""
        statuses = [
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CANCELED,
        ]

        for status in statuses:
            assert status.value in ["scheduled", "confirmed", "canceled"]

    def test_full_appointment_model(self) -> None:
        """Test full appointment model with all fields."""
        from datetime import date, time
        from uuid import uuid4

        now = datetime.now()

        appt = Appointment(
            id=uuid4(),
            customer_id=uuid4(),
            scheduled_date=date(2026, 2, 15),
            scheduled_time=time(14, 0),
            status=AppointmentStatus.SCHEDULED,
            confirmation_code="APPT-ABC123",
            created_at=now,
            updated_at=now,
        )

        assert appt.status == AppointmentStatus.SCHEDULED
        assert appt.confirmation_code == "APPT-ABC123"
