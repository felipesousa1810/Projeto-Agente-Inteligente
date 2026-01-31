"""Unit Tests - Agent Tools Execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.agent import _execute_tool
from src.core.dependencies import AppDependencies


class TestAgentTools:
    """Tests for the _execute_tool function."""

    @pytest.mark.asyncio
    async def test_check_availability_merges_slots(self):
        """Test that check_availability correctly merges internal and external busy slots."""

        context = {"date": "2026-02-15"}

        # Mocks
        mock_supabase_service = MagicMock()
        mock_supabase_service.get_appointments_for_date = AsyncMock(
            return_value=[{"scheduled_time": "14:00:00"}]
        )

        deps = AppDependencies(
            supabase=mock_supabase_service,
            customer_id="customer_123",
            trace_id="trace_123",
        )

        # Mock Calendar Service (ainda obtido via singleton dentro da tool)
        with patch("src.services.calendar.get_calendar_service") as mock_get_calendar:
            mock_calendar = MagicMock()
            mock_calendar.check_availability.return_value = [
                {"start": "2026-02-15T15:00:00Z", "end": "2026-02-15T16:00:00Z"}
            ]
            mock_get_calendar.return_value = mock_calendar

            # Execute
            result = await _execute_tool(
                "check_availability", context, "customer_123", "trace_123", deps
            )

            assert result["available"] is True
            available_slots = result["available_slots"]

            # 14:00 and 15:00 should be removed from defaults
            # Defaults: ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
            assert "14:00" not in available_slots
            assert "15:00" not in available_slots
            assert "09:00" in available_slots

    @pytest.mark.asyncio
    async def test_create_appointment_success(self):
        """Test successful appointment creation logic."""
        context = {"date": "2026-02-15", "time": "10:00", "procedure": "Limpeza"}

        # Mocks
        mock_supabase_service = MagicMock()
        mock_supabase_service.get_or_create_customer = AsyncMock(
            return_value={"id": "uuid-cust", "name": "Test User"}
        )
        mock_supabase_service.create_appointment = AsyncMock(
            return_value={"id": "uuid-appt"}
        )

        deps = AppDependencies(
            supabase=mock_supabase_service,
            customer_id="123456789",
            trace_id="trace_123",
        )

        with patch("src.services.calendar.get_calendar_service") as mock_get_calendar:
            mock_calendar = MagicMock()
            mock_get_calendar.return_value = mock_calendar

            result = await _execute_tool(
                "create_appointment", context, "123456789", "trace_123", deps
            )

            assert result["success"] is True
            assert result["appointment_id"] == "uuid-appt"
            assert "confirmation_code" in result

            # Verify GCal call
            mock_calendar.create_event.assert_called_once()

            # Verify Supabase calls
            mock_supabase_service.get_or_create_customer.assert_called_once()
            mock_supabase_service.create_appointment.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_appointment_flow(self):
        """Test cancel appointment flow."""
        context = {"confirmation_code": "APPT-123"}

        # Mocks
        mock_supabase_service = MagicMock()
        mock_supabase_service.get_appointment_by_code = AsyncMock(
            return_value={"id": "uuid-appt"}
        )
        mock_supabase_service.cancel_appointment = AsyncMock()

        deps = AppDependencies(
            supabase=mock_supabase_service, customer_id="123", trace_id="trace_123"
        )

        result = await _execute_tool(
            "cancel_appointment", context, "123", "trace_123", deps
        )

        assert result["success"] is True
        mock_supabase_service.cancel_appointment.assert_awaited_with("uuid-appt")
