"""Google Calendar Service - Integration with Google Calendar API."""

import json
import os
from datetime import date, datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Scopes required
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:
    """Service to interact with Google Calendar."""

    def __init__(self) -> None:
        """Initialize service with credentials."""
        self.settings = get_settings()
        self.creds = self._authenticate()
        if self.creds:
            self.service = build("calendar", "v3", credentials=self.creds)
        else:
            self.service = None

    def _authenticate(self) -> Any:
        """Authenticate using Service Account or OAuth."""
        creds = None

        # 1. Try Service Account (Preferred for Servers)
        service_account_info = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if service_account_info:
            try:
                # Handle JSON string directly
                if service_account_info.strip().startswith("{"):
                    try:
                        info = json.loads(service_account_info)
                        return service_account.Credentials.from_service_account_info(
                            info, scopes=SCOPES
                        )
                    except json.JSONDecodeError as e:
                        logger.error("gcal_auth_json_error", error=str(e))
                        return None

                # Handle file path
                elif os.path.exists(service_account_info):
                    return service_account.Credentials.from_service_account_file(
                        service_account_info, scopes=SCOPES
                    )
                else:
                    logger.warning(
                        "gcal_auth_invalid_path",
                        path=service_account_info[:20] + "..."
                        if service_account_info
                        else "None",
                    )
            except Exception as e:
                logger.error("gcal_auth_error", error=str(e), type="service_account")

        # 2. Try Local Token (Dev or Env Var)
        token_json = os.environ.get("GOOGLE_TOKEN_JSON")
        if token_json:
            try:
                info = json.loads(token_json)
                creds = Credentials.from_authorized_user_info(info, SCOPES)
            except Exception as e:
                logger.error("gcal_token_env_error", error=str(e))

        if not creds and os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # If we are here in production, it's a failure
                # But for local dev, we might trigger a flow (though not ideal for an agent)
                logger.warning("gcal_no_creds", message="Google Credentials not found.")
                return None

        return creds

    def check_availability(self, check_date: date) -> list[dict[str, Any]]:
        """Check busy slots for a given date.

        Args:
            check_date: Date to check.

        Returns:
            List of busy slots [{'start': datetime, 'end': datetime}]
        """
        if not self.service:
            logger.warning("gcal_service_unavailable")
            return []

        try:
            # Start of day
            time_min = (
                datetime.combine(check_date, datetime.min.time()).isoformat() + "Z"
            )
            # End of day
            time_max = (
                datetime.combine(check_date, datetime.max.time()).isoformat() + "Z"
            )

            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "timeZone": "America/Sao_Paulo",
                "items": [{"id": "primary"}],
            }

            events_result = self.service.freebusy().query(body=body).execute()
            calendars = events_result.get("calendars", {})
            primary_cal = calendars.get("primary", {})
            busy_slots = primary_cal.get("busy", [])

            return busy_slots

        except HttpError as error:
            logger.error("gcal_availability_error", error=str(error))
            return []

    def create_event(
        self,
        summary: str,
        start_dt: datetime,
        end_dt: datetime,
        description: str = "",
        attendee_email: str | None = None,
    ) -> str | None:
        """Create a new calendar event.

        Args:
            summary: Event title.
            start_dt: Start datetime (timezone aware preferably).
            end_dt: End datetime.
            description: Event description.
            attendee_email: Optional email to invite.

        Returns:
            Event ID or None if failed.
        """
        if not self.service:
            return None

        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
        }

        if attendee_email:
            event["attendees"] = [{"email": attendee_email}]

        try:
            event_result = (
                self.service.events().insert(calendarId="primary", body=event).execute()
            )
            event_id = event_result.get("id")
            logger.info("gcal_event_created", event_id=event_id)
            return event_id
        except HttpError as error:
            logger.error("gcal_create_error", error=str(error))
            return None

    def cancel_event(self, event_id: str) -> bool:
        """Cancel an event by ID.

        Args:
            event_id: Google Calendar Event ID.

        Returns:
            True if successful.
        """
        if not self.service:
            return False

        try:
            self.service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()
            logger.info("gcal_event_canceled", event_id=event_id)
            return True
        except HttpError as error:
            logger.error("gcal_cancel_error", error=str(error))
            return False


# Singleton
_calendar_service = None


def get_calendar_service() -> GoogleCalendarService:
    """Get singleton instance."""
    global _calendar_service
    if not _calendar_service:
        _calendar_service = GoogleCalendarService()
    return _calendar_service
