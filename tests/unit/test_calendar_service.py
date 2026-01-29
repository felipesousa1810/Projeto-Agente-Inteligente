"""Unit Tests - Google Calendar Service."""

from datetime import date
from unittest.mock import MagicMock, patch

from src.services.calendar import GoogleCalendarService


class TestGoogleCalendarService:
    """Tests for the Google Calendar Service wrapper."""

    @patch("src.services.calendar.build")
    @patch("src.services.calendar.get_settings")
    @patch("src.services.calendar.GoogleCalendarService._authenticate")
    def test_check_availability_returns_slots(
        self, mock_auth, mock_settings, mock_build
    ):
        """Test check_availability parses API response correctly."""
        # Setup mocks
        mock_auth.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock freebusy response
        mock_service.freebusy().query().execute.return_value = {
            "calendars": {
                "primary": {
                    "busy": [
                        {"start": "2026-02-15T14:00:00Z", "end": "2026-02-15T15:00:00Z"}
                    ]
                }
            }
        }

        service = GoogleCalendarService()
        check_date = date(2026, 2, 15)

        busy_slots = service.check_availability(check_date)

        assert len(busy_slots) == 1
        assert busy_slots[0]["start"] == "2026-02-15T14:00:00Z"

    @patch("src.services.calendar.build")
    @patch("src.services.calendar.get_settings")
    @patch("src.services.calendar.GoogleCalendarService._authenticate")
    def test_check_availability_handles_api_error(
        self, mock_auth, mock_settings, mock_build
    ):
        """Test check_availability handles HttpError gracefully."""
        from googleapiclient.errors import HttpError

        mock_build.return_value.freebusy().query().execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b"Error"
        )

        service = GoogleCalendarService()
        check_date = date(2026, 2, 15)

        busy_slots = service.check_availability(check_date)

        assert busy_slots == []
