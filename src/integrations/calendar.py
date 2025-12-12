"""Google Calendar integration for meeting scheduling."""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class CalendarService:
    """
    Service for Google Calendar operations.

    Uses service account with domain-wide delegation
    for booking meetings on behalf of users.
    """

    def __init__(self):
        """Initialize service."""
        self._service = None
        self._settings = None
        self._available = None

    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def service(self):
        """Lazy initialize Google Calendar service."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        """Build Google Calendar service with service account."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials_path = self.settings.GOOGLE_CREDENTIALS_PATH

            if not os.path.exists(credentials_path):
                logger.warning(f"Google credentials not found: {credentials_path}")
                return None

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/calendar"]
            )

            # Delegate to calendar owner
            delegated_credentials = credentials.with_subject(
                self.settings.GOOGLE_CALENDAR_ID
            )

            service = build("calendar", "v3", credentials=delegated_credentials)
            logger.info("Google Calendar service initialized")
            return service

        except ImportError:
            logger.error("google-api-python-client not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Calendar service: {e}")
            return None

    def is_available(self) -> bool:
        """Check if calendar service is available."""
        if self._available is None:
            self._available = self.service is not None
        return self._available

    def parse_meeting_time(self, time_string: str) -> Optional[datetime]:
        """
        Parse natural language meeting time.

        Args:
            time_string: Natural language time (e.g., "Thursday at 10am")

        Returns:
            Parsed datetime or None
        """
        if not time_string:
            return None

        try:
            # Try direct parsing
            parsed = date_parser.parse(time_string, fuzzy=True)

            # If parsed date is in the past, assume next occurrence
            now = datetime.now()
            if parsed < now:
                if parsed.date() == now.date():
                    # Same day but time passed - assume tomorrow
                    parsed += timedelta(days=1)
                elif parsed < now - timedelta(days=1):
                    # More than a day ago - add a week
                    parsed += timedelta(weeks=1)

            return parsed

        except Exception as e:
            logger.warning(f"Could not parse meeting time '{time_string}': {e}")
            return None

    def find_available_slot(
        self,
        start_from: datetime,
        duration_minutes: int = 30,
        days_ahead: int = 7
    ) -> Optional[datetime]:
        """
        Find next available time slot.

        Args:
            start_from: Start searching from this time
            duration_minutes: Meeting duration
            days_ahead: How many days to search

        Returns:
            Next available datetime
        """
        if not self.is_available():
            return None

        try:
            # Business hours: 9 AM to 5 PM
            business_start = 9
            business_end = 17

            end_date = start_from + timedelta(days=days_ahead)

            # Query busy times
            body = {
                "timeMin": start_from.isoformat() + "Z",
                "timeMax": end_date.isoformat() + "Z",
                "items": [{"id": self.settings.GOOGLE_CALENDAR_ID}]
            }

            result = self.service.freebusy().query(body=body).execute()
            busy_times = result.get("calendars", {}).get(
                self.settings.GOOGLE_CALENDAR_ID, {}
            ).get("busy", [])

            # Find first available slot
            current = start_from.replace(minute=0, second=0, microsecond=0)
            if current.hour < business_start:
                current = current.replace(hour=business_start)
            elif current.hour >= business_end:
                current = (current + timedelta(days=1)).replace(hour=business_start)

            while current < end_date:
                # Skip weekends
                if current.weekday() >= 5:
                    current = (current + timedelta(days=1)).replace(hour=business_start)
                    continue

                # Check if within business hours
                if current.hour >= business_end:
                    current = (current + timedelta(days=1)).replace(hour=business_start)
                    continue

                # Check if slot is free
                slot_end = current + timedelta(minutes=duration_minutes)
                is_free = True

                for busy in busy_times:
                    busy_start = date_parser.parse(busy["start"])
                    busy_end = date_parser.parse(busy["end"])

                    if not (slot_end <= busy_start or current >= busy_end):
                        is_free = False
                        break

                if is_free:
                    return current

                current += timedelta(minutes=30)

            return None

        except Exception as e:
            logger.error(f"Failed to find available slot: {e}")
            return None

    def create_meeting(
        self,
        attendee_email: str,
        company_name: str,
        meeting_time: datetime,
        duration_minutes: int = 30
    ) -> Optional[str]:
        """
        Create a calendar meeting.

        Args:
            attendee_email: Attendee's email
            company_name: Company name for meeting title
            meeting_time: Meeting start time
            duration_minutes: Meeting duration

        Returns:
            Meeting link/URL if successful
        """
        if not self.is_available():
            return None

        try:
            end_time = meeting_time + timedelta(minutes=duration_minutes)

            event = {
                "summary": f"Nodari AI x {company_name} - Discovery Call",
                "description": f"""
Discovery call to discuss AI solutions for {company_name}.

Agenda:
- Understand your current challenges
- Discuss potential AI solutions
- Outline next steps

Looking forward to speaking with you!

- Nodari AI Team
                """.strip(),
                "start": {
                    "dateTime": meeting_time.isoformat(),
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "America/New_York"
                },
                "attendees": [
                    {"email": attendee_email},
                    {"email": self.settings.GOOGLE_CALENDAR_ID}
                ],
                "conferenceData": {
                    "createRequest": {
                        "requestId": f"nodari-{company_name}-{meeting_time.timestamp()}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"}
                    }
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 60},
                        {"method": "popup", "minutes": 15}
                    ]
                }
            }

            result = self.service.events().insert(
                calendarId=self.settings.GOOGLE_CALENDAR_ID,
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all"
            ).execute()

            meeting_link = result.get("hangoutLink") or result.get("htmlLink")
            logger.info(f"Meeting created: {meeting_link}")
            return meeting_link

        except Exception as e:
            logger.error(f"Failed to create meeting: {e}")
            return None


# Singleton instance
calendar_service = CalendarService()
