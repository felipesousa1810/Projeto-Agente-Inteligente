"""Unit Tests - Agent Tools Execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.agent import _execute_tool


class TestAgentTools:
    """Tests for the _execute_tool function."""

    @pytest.mark.asyncio
    async def test_check_availability_merges_slots(self):
        """Test that check_availability correctly merges internal and external busy slots."""

        context = {"date": "2026-02-15"}

        # Mock dependencies
        with (
            patch(
                "src.services.supabase.get_appointments_for_date",
                new_callable=AsyncMock,
            ) as mock_db_get,
            patch("src.services.calendar.get_calendar_service") as mock_get_calendar,
        ):
            # Setup DB mock (busy at 14:00)
            mock_db_get.return_value = [{"scheduled_time": "14:00:00"}]

            # Setup Calendar mock (busy at 15:00)
            mock_calendar = MagicMock()
            mock_calendar.check_availability.return_value = [
                {"start": "2026-02-15T15:00:00Z", "end": "2026-02-15T16:00:00Z"}
            ]
            mock_get_calendar.return_value = mock_calendar

            # Execute
            result = await _execute_tool(
                "check_availability", context, "customer_123", "trace_123"
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

        with (
            patch(
                "src.services.supabase.get_or_create_customer", new_callable=AsyncMock
            ) as mock_get_customer,
            patch(
                "src.services.supabase.create_appointment", new_callable=AsyncMock
            ) as mock_create_appt,
            patch("src.services.calendar.get_calendar_service") as mock_get_calendar,
        ):
            # Mocks
            mock_get_customer.return_value = {"id": "uuid-cust", "name": "Test User"}
            mock_create_appt.return_value = {"id": "uuid-appt"}
            mock_calendar = MagicMock()
            mock_get_calendar.return_value = mock_calendar

            result = await _execute_tool(
                "create_appointment", context, "123456789", "trace_123"
            )

            assert result["success"] is True
            assert result["appointment_id"] == "uuid-appt"
            assert "confirmation_code" in result

            # Verify GCal call
            mock_calendar.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_appointment_flow(self):
        """Test cancel appointment flow."""
        context = {"confirmation_code": "APPT-123"}

        with (
            patch(
                "src.services.supabase.get_appointment_by_code", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "src.services.supabase.cancel_appointment", new_callable=AsyncMock
            ) as mock_cancel,
        ):
            mock_get.return_value = {"id": "uuid-appt"}

            result = await _execute_tool(
                "cancel_appointment", context, "123", "trace_123"
            )

            assert result["success"] is True
            mock_cancel.assert_awaited_with("uuid-appt")
