"""Google Calendar integration tool for meeting scheduling."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import get_settings

logger = logging.getLogger(__name__)


class CalendarService:
    """
    Google Calendar service for booking discovery calls.

    Uses a service account with domain-wide delegation to
    create calendar events on behalf of the organization.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
    ]

    def __init__(self):
        """Initialize Google Calendar client."""
        settings = get_settings()
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.credentials_path = settings.GOOGLE_CREDENTIALS_PATH

        # Initialize credentials and service
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Calendar API service."""
        try:
            creds_path = Path(self.credentials_path)
            if not creds_path.exists():
                logger.warning(
                    f"Google credentials file not found: {self.credentials_path}. "
                    "Calendar features will be disabled."
                )
                return

            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                str(creds_path),
                scopes=self.SCOPES
            )

            # If using domain-wide delegation, impersonate the calendar owner
            # This requires admin setup in Google Workspace
            credentials = credentials.with_subject(self.calendar_id)

            # Build the calendar service
            self.service = build("calendar", "v3", credentials=credentials)
            logger.info(f"Google Calendar service initialized for {self.calendar_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar: {e}")
            self.service = None

    def is_available(self) -> bool:
        """Check if calendar service is available."""
        return self.service is not None

    def create_meeting(
        self,
        attendee_email: str,
        company_name: str,
        meeting_time: datetime,
        duration_minutes: int = 30,
        description: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a calendar event for a discovery call.

        Args:
            attendee_email: Email of the attendee
            company_name: Company name for event title
            meeting_time: Start time of the meeting
            duration_minutes: Duration in minutes (default 30)
            description: Optional custom description

        Returns:
            HTML link to the calendar event, or None on failure
        """
        if not self.service:
            logger.error("Calendar service not initialized")
            return None

        try:
            end_time = meeting_time + timedelta(minutes=duration_minutes)

            # Build event description
            event_description = description or f"""Discovery call to discuss AI solutions for {company_name}.

This meeting was automatically scheduled following a successful initial conversation.

Agenda:
1. Review your AI requirements and goals
2. Discuss potential solutions and approaches
3. Timeline and next steps

Looking forward to speaking with you!

- The Nodari AI Team
"""

            # Create event body
            event = {
                "summary": f"Nodari AI - Discovery Call with {company_name}",
                "description": event_description,
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
                    {"email": self.calendar_id}
                ],
                # Create Google Meet link
                "conferenceData": {
                    "createRequest": {
                        "requestId": f"nodari-{datetime.now().timestamp()}",
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

            # Insert the event
            result = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all"  # Send invitations to attendees
            ).execute()

            event_link = result.get("htmlLink")
            event_id = result.get("id")

            logger.info(f"Calendar event created: {event_id} for {company_name}")
            return event_link

        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    def find_available_slot(
        self,
        preferred_date: datetime,
        duration_minutes: int = 30,
        business_hours_start: int = 9,
        business_hours_end: int = 17,
        days_to_search: int = 7
    ) -> Optional[datetime]:
        """
        Find next available time slot near preferred date.

        Args:
            preferred_date: Preferred meeting date
            duration_minutes: Required duration
            business_hours_start: Start of business hours (hour)
            business_hours_end: End of business hours (hour)
            days_to_search: Number of days to search forward

        Returns:
            Available datetime slot, or None if not found
        """
        if not self.service:
            logger.error("Calendar service not initialized")
            return None

        try:
            # Set search bounds
            time_min = preferred_date.replace(
                hour=business_hours_start, minute=0, second=0, microsecond=0
            )
            time_max = (preferred_date + timedelta(days=days_to_search)).replace(
                hour=business_hours_end, minute=0, second=0, microsecond=0
            )

            # Get busy periods
            body = {
                "timeMin": time_min.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "items": [{"id": self.calendar_id}]
            }

            freebusy = self.service.freebusy().query(body=body).execute()
            busy_periods = freebusy.get("calendars", {}).get(
                self.calendar_id, {}
            ).get("busy", [])

            # Find first available slot
            current = time_min
            while current < time_max:
                # Skip outside business hours
                if current.hour < business_hours_start:
                    current = current.replace(hour=business_hours_start, minute=0)
                    continue
                if current.hour >= business_hours_end:
                    current = (current + timedelta(days=1)).replace(
                        hour=business_hours_start, minute=0
                    )
                    continue

                # Skip weekends
                if current.weekday() >= 5:
                    days_until_monday = 7 - current.weekday()
                    current = (current + timedelta(days=days_until_monday)).replace(
                        hour=business_hours_start, minute=0
                    )
                    continue

                # Check if this slot is free
                slot_end = current + timedelta(minutes=duration_minutes)
                is_free = True

                for busy in busy_periods:
                    busy_start = datetime.fromisoformat(
                        busy["start"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    busy_end = datetime.fromisoformat(
                        busy["end"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)

                    # Check for overlap
                    if current < busy_end and slot_end > busy_start:
                        is_free = False
                        # Jump to end of this busy period
                        current = busy_end
                        break

                if is_free:
                    logger.info(f"Found available slot: {current}")
                    return current

                # Move to next slot (30-minute increments)
                current += timedelta(minutes=30)

            logger.warning("No available slots found in search range")
            return None

        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to find available slot: {e}")
            return None

    def parse_meeting_time(
        self,
        time_string: str,
        reference_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Parse natural language meeting time to datetime.

        Args:
            time_string: Natural language time (e.g., "Wednesday at 3pm")
            reference_date: Reference date for relative times

        Returns:
            Parsed datetime, or None if parsing fails
        """
        if not time_string:
            return None

        reference = reference_date or datetime.now()

        # Common patterns to try
        time_lower = time_string.lower()

        try:
            # Try direct parsing first
            from dateutil import parser as date_parser
            parsed = date_parser.parse(time_string, default=reference)
            return parsed
        except Exception:
            pass

        # Fallback: return None and let caller handle
        logger.warning(f"Could not parse meeting time: {time_string}")
        return None


# ===========================================
# Singleton Instance
# ===========================================

calendar_service = CalendarService()
