"""Supabase database service for Nodari Sales Engine."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Service for Supabase database operations.

    Handles all CRUD operations for the nodari_inquiries table.
    Uses sync Supabase client but exposed through async interface
    for consistency with the rest of the application.
    """

    TABLE_NAME = "nodari_inquiries"

    def __init__(self):
        """Initialize Supabase client."""
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy initialization of Supabase client."""
        if self._client is None:
            settings = get_settings()
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("Supabase credentials not configured")

            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY,
                options=ClientOptions(
                    postgrest_client_timeout=30,
                    storage_client_timeout=30
                )
            )
            logger.info("Supabase client initialized")
        return self._client

    # ===========================================
    # Create Operations
    # ===========================================

    async def create_inquiry(self, lead: "ParsedLead") -> Optional[str]:
        """Create a new inquiry record from parsed lead data."""
        try:
            data = lead.model_dump(exclude_none=True, exclude={"raw_form_data"})
            data["status"] = "new"
            data["created_at"] = datetime.utcnow().isoformat()

            if lead.raw_form_data:
                data["raw_form_data"] = lead.raw_form_data

            response = self.client.table(self.TABLE_NAME).insert(data).execute()

            if response.data and len(response.data) > 0:
                inquiry_id = response.data[0].get("id")
                logger.info(f"Created inquiry: {inquiry_id}")
                return inquiry_id

            logger.error("Insert returned no data")
            return None

        except Exception as e:
            logger.error(f"Failed to create inquiry: {e}")
            return None

    # ===========================================
    # Read Operations
    # ===========================================

    async def get_inquiry(self, inquiry_id: str) -> Optional["InquiryRecord"]:
        """Fetch inquiry by ID."""
        try:
            from src.models import InquiryRecord

            response = (
                self.client.table(self.TABLE_NAME)
                .select("*")
                .eq("id", inquiry_id)
                .single()
                .execute()
            )

            if response.data:
                return InquiryRecord(**response.data)

            logger.warning(f"Inquiry not found: {inquiry_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get inquiry {inquiry_id}: {e}")
            return None

    async def get_inquiry_by_call_id(self, call_id: str) -> Optional["InquiryRecord"]:
        """Fetch inquiry by Retell call ID."""
        try:
            from src.models import InquiryRecord

            response = (
                self.client.table(self.TABLE_NAME)
                .select("*")
                .eq("retell_call_id", call_id)
                .single()
                .execute()
            )

            if response.data:
                return InquiryRecord(**response.data)

            logger.warning(f"Inquiry not found for call_id: {call_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get inquiry by call_id {call_id}: {e}")
            return None

    async def get_inquiries_by_status(
        self,
        status: str,
        limit: int = 100
    ) -> List["InquiryRecord"]:
        """Fetch inquiries by status."""
        try:
            from src.models import InquiryRecord

            response = (
                self.client.table(self.TABLE_NAME)
                .select("*")
                .eq("status", status)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            if response.data:
                return [InquiryRecord(**record) for record in response.data]
            return []

        except Exception as e:
            logger.error(f"Failed to get inquiries by status {status}: {e}")
            return []

    # ===========================================
    # Update Operations
    # ===========================================

    async def update_inquiry(
        self,
        inquiry_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update inquiry with partial data."""
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()

            response = (
                self.client.table(self.TABLE_NAME)
                .update(updates)
                .eq("id", inquiry_id)
                .execute()
            )

            if response.data:
                logger.info(f"Updated inquiry {inquiry_id}: {list(updates.keys())}")
                return True

            logger.warning(f"Update returned no data for {inquiry_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to update inquiry {inquiry_id}: {e}")
            return False

    async def update_research(
        self,
        inquiry_id: str,
        research_data: Optional[Dict[str, Any]],
        lead_score: int,
        lead_category: str,
        scoring_details: Optional[Dict[str, Any]]
    ) -> bool:
        """Update inquiry with research and scoring results."""
        return await self.update_inquiry(inquiry_id, {
            "company_research": research_data,
            "lead_score": lead_score,
            "lead_category": lead_category,
            "scoring_details": scoring_details,
            "status": "researched"
        })

    async def update_call_initiated(self, inquiry_id: str, call_id: str) -> bool:
        """Update inquiry when Retell call is initiated."""
        return await self.update_inquiry(inquiry_id, {
            "retell_call_id": call_id,
            "status": "call_initiated"
        })

    async def update_call_completed(
        self,
        inquiry_id: str,
        transcript: str,
        recording_url: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ) -> bool:
        """Update inquiry when call completes."""
        updates: Dict[str, Any] = {
            "call_transcript": transcript,
            "status": "call_completed"
        }
        if recording_url:
            updates["call_recording_url"] = recording_url
        if duration_seconds:
            updates["call_duration_seconds"] = duration_seconds

        return await self.update_inquiry(inquiry_id, updates)

    async def update_call_analysis(
        self,
        inquiry_id: str,
        analysis_data: Dict[str, Any]
    ) -> bool:
        """Update inquiry with post-call analysis."""
        return await self.update_inquiry(inquiry_id, {
            "call_analysis": analysis_data,
            "status": "analyzed"
        })

    async def update_hot_processed(
        self,
        inquiry_id: str,
        proposal_url: str,
        meeting_booked: bool = False,
        meeting_link: Optional[str] = None
    ) -> bool:
        """Update inquiry after hot lead processing."""
        updates: Dict[str, Any] = {
            "proposal_url": proposal_url,
            "meeting_booked": meeting_booked,
            "followup_sent": True,
            "status": "hot_processed"
        }
        if meeting_link:
            updates["meeting_link"] = meeting_link

        return await self.update_inquiry(inquiry_id, updates)

    async def update_warm_processed(self, inquiry_id: str) -> bool:
        """Update inquiry after warm lead processing."""
        return await self.update_inquiry(inquiry_id, {
            "followup_sent": True,
            "status": "warm_processed"
        })

    async def update_nurture_processed(self, inquiry_id: str) -> bool:
        """Update inquiry after nurture lead processing."""
        return await self.update_inquiry(inquiry_id, {
            "followup_sent": True,
            "status": "nurture_processed"
        })

    async def update_status(self, inquiry_id: str, status: str) -> bool:
        """Update inquiry status."""
        return await self.update_inquiry(inquiry_id, {"status": status})

    # ===========================================
    # Health Check
    # ===========================================

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            self.client.table(self.TABLE_NAME).select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Forward reference imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models import ParsedLead, InquiryRecord

# Singleton instance
db_service = DatabaseService()
