"""Lead Processor Service - Main orchestration for both flows with async support."""

import logging
from typing import Dict, Any, Optional

from src.core.config import get_settings, map_form_fields, format_phone_number
from src.core.database import db_service
from src.models import (
    ParsedLead,
    InquiryRecord,
    RetellWebhookPayload,
    PreCallResult,
    PostCallResult,
    LeadStatus
)
from src.intelligence.crews.pre_call import PreCallCrew
from src.intelligence.crews.post_call import PostCallCrew
from src.integrations.retell import retell_service

logger = logging.getLogger(__name__)


class LeadProcessor:
    """
    Main orchestration service for lead processing.

    Handles both flows:
    1. Form submission → Pre-call intelligence → Retell call
    2. Retell webhook → Post-call analysis → Follow-up actions

    All heavy processing is async-safe using asyncio.to_thread().
    """

    def __init__(self):
        """Initialize processor with lazy-loaded dependencies."""
        self._settings = None
        self._pre_call_crew = None
        self._post_call_crew = None
        logger.info("Lead processor initialized")

    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def parse_form_submission(self, raw_data: Dict[str, Any]) -> ParsedLead:
        """
        Parse raw form data into normalized lead model.

        Args:
            raw_data: Raw JSON from Google Apps Script

        Returns:
            ParsedLead with normalized field names
        """
        mapped_data = map_form_fields(raw_data)
        mapped_data["raw_form_data"] = raw_data

        # Format phone number
        if mapped_data.get("phone"):
            mapped_data["phone"] = format_phone_number(mapped_data["phone"])

        lead = ParsedLead(**mapped_data)

        logger.info(f"Parsed lead: {lead.company_name} ({lead.email})")
        return lead

    async def process_form_webhook(self, raw_data: Dict[str, Any]) -> str:
        """
        Process Flow 1: Form submission to Retell call.

        This is now fully async-safe. Heavy AI processing runs
        in background threads.

        Steps:
        1. Parse and validate form data
        2. Save to Supabase
        3. Run pre-call crew (async)
        4. Trigger Retell call with dynamic variables

        Args:
            raw_data: Raw form submission

        Returns:
            Inquiry ID
        """
        logger.info("Processing form webhook")

        # Step 1: Parse form data
        lead = self.parse_form_submission(raw_data)

        # Step 2: Create inquiry in database
        inquiry_id = await db_service.create_inquiry(lead)

        if not inquiry_id:
            logger.error("Failed to create inquiry record")
            raise Exception("Database error: Could not create inquiry")

        logger.info(f"Created inquiry {inquiry_id} for {lead.company_name}")

        # Step 3: Run pre-call crew (async-safe)
        pre_call_result = await self._run_pre_call_pipeline(lead, inquiry_id)

        # Step 4: Trigger Retell call if we have a phone number
        if lead.phone:
            await self._trigger_retell_call(lead, inquiry_id, pre_call_result)
        else:
            logger.warning(f"No phone number for {inquiry_id} - skipping call")
            await db_service.update_status(inquiry_id, LeadStatus.RESEARCH_COMPLETE.value)

        return inquiry_id

    async def process_retell_webhook(self, payload: RetellWebhookPayload) -> None:
        """
        Process Flow 2: Retell webhook to post-call actions.

        Steps:
        1. Find inquiry by call_id
        2. Update with call data
        3. Run post-call crew (async)
        4. Update database with results

        Args:
            payload: Retell webhook payload
        """
        if payload.event != "call_analyzed":
            logger.info(f"Ignoring Retell event: {payload.event}")
            return

        call_id = payload.get_call_id()
        logger.info(f"Processing Retell webhook for call_id: {call_id}")

        # Step 1: Find inquiry
        inquiry = await db_service.get_inquiry_by_call_id(call_id)

        if not inquiry:
            logger.error(f"No inquiry found for call_id: {call_id}")
            return

        inquiry_id = inquiry.id
        logger.info(f"Found inquiry {inquiry_id} for call {call_id}")

        # Step 2: Extract call data
        transcript = payload.get_transcript()
        recording_url = payload.get_recording_url()
        duration = payload.get_duration()
        call_summary = payload.get_call_summary()

        # Update with call data
        await db_service.update_call_completed(
            inquiry_id,
            transcript=transcript,
            recording_url=recording_url,
            duration_seconds=duration
        )

        # Step 3: Run post-call crew (async-safe)
        post_call_result = await self._run_post_call_pipeline(
            inquiry,
            transcript,
            call_summary,
            recording_url
        )

        # Step 4: Update database with results
        await self._update_post_call_results(inquiry_id, post_call_result)

    async def _run_pre_call_pipeline(
        self,
        lead: ParsedLead,
        inquiry_id: str
    ) -> PreCallResult:
        """
        Run the pre-call intelligence pipeline asynchronously.

        Args:
            lead: Parsed lead data
            inquiry_id: Database record ID

        Returns:
            PreCallResult with research, scoring, personalization
        """
        try:
            logger.info(f"Running pre-call pipeline for {inquiry_id}")

            # Initialize crew if needed
            if not self._pre_call_crew:
                self._pre_call_crew = PreCallCrew()

            # Run the crew asynchronously
            result = await self._pre_call_crew.run_async(lead)

            # Update database with results
            if result.research or result.scoring:
                await db_service.update_research(
                    inquiry_id,
                    research_data=result.research.model_dump() if result.research else None,
                    lead_score=result.scoring.total_score if result.scoring else 50,
                    lead_category=result.scoring.category.value if result.scoring else "warm",
                    scoring_details=result.scoring.model_dump() if result.scoring else None
                )

            return result

        except Exception as e:
            logger.error(f"Pre-call pipeline failed for {inquiry_id}: {e}")
            await db_service.update_status(inquiry_id, LeadStatus.RESEARCH_FAILED.value)
            return PreCallResult(success=False, errors=[str(e)])

    async def _trigger_retell_call(
        self,
        lead: ParsedLead,
        inquiry_id: str,
        pre_call_result: PreCallResult
    ) -> Optional[str]:
        """
        Trigger a Retell call with intelligence context.

        Args:
            lead: Lead data
            inquiry_id: Database record ID
            pre_call_result: Pre-call crew output

        Returns:
            Call ID if successful
        """
        try:
            logger.info(f"Triggering Retell call for {inquiry_id}")

            # Build dynamic variables
            if pre_call_result.personalization and pre_call_result.research:
                dynamic_vars = retell_service.build_dynamic_variables(
                    company_name=lead.company_name,
                    contact_name=lead.company_name,
                    email=lead.email,
                    website=lead.website,
                    primary_goal=lead.primary_goal,
                    business_challenges=lead.business_challenges,
                    timeline=lead.timeline,
                    research_summary=pre_call_result.research.company_summary,
                    personalization=pre_call_result.personalization
                )
            else:
                dynamic_vars = retell_service.build_minimal_variables(
                    company_name=lead.company_name,
                    email=lead.email,
                    primary_goal=lead.primary_goal,
                    business_challenges=lead.business_challenges
                )

            # Create call
            call_id = await retell_service.create_call(
                to_number=lead.phone,
                dynamic_variables=dynamic_vars,
                metadata={
                    "inquiry_id": inquiry_id,
                    "company_name": lead.company_name
                }
            )

            if call_id:
                await db_service.update_call_initiated(inquiry_id, call_id)
                logger.info(f"Retell call initiated: {call_id}")
                return call_id
            else:
                await db_service.update_status(inquiry_id, LeadStatus.CALL_FAILED.value)
                logger.error(f"Failed to initiate Retell call for {inquiry_id}")
                return None

        except Exception as e:
            logger.error(f"Error triggering Retell call for {inquiry_id}: {e}")
            await db_service.update_status(inquiry_id, LeadStatus.CALL_FAILED.value)
            return None

    async def _run_post_call_pipeline(
        self,
        inquiry: InquiryRecord,
        transcript: str,
        call_summary: str,
        recording_url: Optional[str]
    ) -> PostCallResult:
        """
        Run the post-call processing pipeline asynchronously.

        Args:
            inquiry: Original inquiry record
            transcript: Call transcript
            call_summary: Retell call summary
            recording_url: Recording URL

        Returns:
            PostCallResult with analysis and actions
        """
        try:
            logger.info(f"Running post-call pipeline for {inquiry.id}")

            if not self._post_call_crew:
                self._post_call_crew = PostCallCrew()

            # Run the crew asynchronously
            result = await self._post_call_crew.run_async(
                inquiry=inquiry,
                transcript=transcript,
                call_summary=call_summary,
                recording_url=recording_url
            )

            return result

        except Exception as e:
            logger.error(f"Post-call pipeline failed for {inquiry.id}: {e}")
            return PostCallResult(success=False, errors=[str(e)])

    async def _update_post_call_results(
        self,
        inquiry_id: str,
        result: PostCallResult
    ) -> None:
        """Update database with post-call results."""
        try:
            if result.analysis:
                await db_service.update_call_analysis(
                    inquiry_id,
                    result.analysis.model_dump()
                )

            if result.proposal_pdf_path or result.meeting_booked:
                await db_service.update_hot_processed(
                    inquiry_id,
                    proposal_url=result.proposal_pdf_path or "",
                    meeting_booked=result.meeting_booked,
                    meeting_link=result.meeting_link
                )
            elif result.email_sent and result.analysis:
                interest = result.analysis.interest_level
                if interest >= self.settings.WARM_THRESHOLD:
                    await db_service.update_warm_processed(inquiry_id)
                else:
                    await db_service.update_nurture_processed(inquiry_id)

            logger.info(f"Updated post-call results for {inquiry_id}")

        except Exception as e:
            logger.error(f"Failed to update post-call results for {inquiry_id}: {e}")

    async def get_inquiry_status(self, inquiry_id: str) -> Optional[InquiryRecord]:
        """Get full inquiry status."""
        return await db_service.get_inquiry(inquiry_id)


# Singleton instance
lead_processor = LeadProcessor()
