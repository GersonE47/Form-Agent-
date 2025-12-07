"""Lead Processor Service - Main orchestration for both flows."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.config import get_settings, map_form_fields, format_phone_number, LeadStatus
from src.database import db_service
from src.models import (
    ParsedLead,
    InquiryRecord,
    RetellWebhookPayload,
    PreCallResult,
    PostCallResult
)
from src.crews.pre_call_crew import PreCallCrew
from src.crews.post_call_crew import PostCallCrew
from src.tools.retell_caller import RetellCaller

logger = logging.getLogger(__name__)


class LeadProcessor:
    """
    Main orchestration service for lead processing.

    Handles both flows:
    1. Form submission → Pre-call intelligence → Retell call
    2. Retell webhook → Post-call analysis → Follow-up actions
    """

    def __init__(self):
        """Initialize processor with all dependencies."""
        self.settings = get_settings()
        self.retell = RetellCaller()
        self.pre_call_crew = None  # Lazy initialization
        self.post_call_crew = None  # Lazy initialization

        logger.info("Lead processor initialized")

    def parse_form_submission(self, raw_data: Dict[str, Any]) -> ParsedLead:
        """
        Parse raw form data into normalized lead model.

        Args:
            raw_data: Raw JSON from Google Apps Script

        Returns:
            ParsedLead with normalized field names
        """
        # Map form fields to internal names
        mapped_data = map_form_fields(raw_data)

        # Store raw data for reference
        mapped_data["raw_form_data"] = raw_data

        # Create lead model
        lead = ParsedLead(**mapped_data)

        logger.info(
            f"Parsed lead: {lead.company_name} ({lead.email})"
        )

        return lead

    async def process_form_webhook(
        self,
        raw_data: Dict[str, Any]
    ) -> str:
        """
        Process Flow 1: Form submission to Retell call.

        Steps:
        1. Parse and validate form data
        2. Save to Supabase
        3. Run pre-call crew (Research → Scoring → Personalization)
        4. Trigger Retell call with dynamic variables

        Args:
            raw_data: Raw form submission from Google Apps Script

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

        # Step 3: Run pre-call crew
        pre_call_result = await self._run_pre_call_pipeline(
            lead,
            inquiry_id
        )

        # Step 4: Trigger Retell call if we have a phone number
        if lead.phone:
            await self._trigger_retell_call(
                lead,
                inquiry_id,
                pre_call_result
            )
        else:
            logger.warning(f"No phone number for {inquiry_id} - skipping Retell call")
            await db_service.update_status(inquiry_id, LeadStatus.RESEARCH_FAILED)

        return inquiry_id

    async def process_retell_webhook(
        self,
        payload: RetellWebhookPayload
    ) -> None:
        """
        Process Flow 2: Retell webhook to post-call actions.

        Steps:
        1. Find inquiry by call_id
        2. Update with call data
        3. Run post-call crew (Analysis → Routing → Actions)
        4. Update database with results

        Args:
            payload: Retell webhook payload
        """
        if payload.event != "call_analyzed":
            logger.info(f"Ignoring Retell event: {payload.event}")
            return

        call_data = payload.call
        call_id = call_data.get("call_id")

        logger.info(f"Processing Retell webhook for call_id: {call_id}")

        # Step 1: Find inquiry
        inquiry = await db_service.get_inquiry_by_call_id(call_id)

        if not inquiry:
            logger.error(f"No inquiry found for call_id: {call_id}")
            return

        inquiry_id = inquiry.id
        logger.info(f"Found inquiry {inquiry_id} for call {call_id}")

        # Step 2: Extract call data
        transcript = call_data.get("transcript", "")
        recording_url = call_data.get("recording_url")
        duration = call_data.get("call_length_sec") or call_data.get("duration_seconds")
        call_summary = call_data.get("call_analysis", {}).get("call_summary", "")

        # Update with call data
        await db_service.update_call_completed(
            inquiry_id,
            transcript=transcript,
            recording_url=recording_url,
            duration_seconds=duration
        )

        # Step 3: Run post-call crew
        post_call_result = await self._run_post_call_pipeline(
            inquiry,
            transcript,
            call_summary,
            recording_url
        )

        # Step 4: Update database with results
        await self._update_post_call_results(
            inquiry_id,
            post_call_result
        )

    async def _run_pre_call_pipeline(
        self,
        lead: ParsedLead,
        inquiry_id: str
    ) -> PreCallResult:
        """
        Run the pre-call intelligence pipeline.

        Uses graceful degradation - if crew fails, still returns
        minimal result that can be used for the call.

        Args:
            lead: Parsed lead data
            inquiry_id: Database record ID

        Returns:
            PreCallResult with research, scoring, personalization
        """
        try:
            logger.info(f"Running pre-call pipeline for {inquiry_id}")

            # Initialize crew if needed
            if not self.pre_call_crew:
                self.pre_call_crew = PreCallCrew()

            # Run the crew
            result = self.pre_call_crew.run(lead)

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

            # Update status
            await db_service.update_status(inquiry_id, LeadStatus.RESEARCH_FAILED)

            # Return minimal result
            return PreCallResult(
                success=False,
                errors=[str(e)]
            )

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
                dynamic_vars = self.retell.build_dynamic_variables(
                    company_name=lead.company_name,
                    contact_name=lead.company_name,  # Using company name
                    email=lead.email,
                    website=lead.website,
                    primary_goal=lead.primary_goal,
                    business_challenges=lead.business_challenges,
                    timeline=lead.timeline,
                    research_summary=pre_call_result.research.company_summary,
                    personalization=pre_call_result.personalization
                )
            else:
                # Fallback to minimal variables
                dynamic_vars = self.retell.build_minimal_variables(
                    company_name=lead.company_name,
                    email=lead.email,
                    primary_goal=lead.primary_goal,
                    business_challenges=lead.business_challenges
                )

            # Create call
            call_id = await self.retell.create_call(
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
                await db_service.update_status(inquiry_id, LeadStatus.CALL_FAILED)
                logger.error(f"Failed to initiate Retell call for {inquiry_id}")
                return None

        except Exception as e:
            logger.error(f"Error triggering Retell call for {inquiry_id}: {e}")
            await db_service.update_status(inquiry_id, LeadStatus.CALL_FAILED)
            return None

    async def _run_post_call_pipeline(
        self,
        inquiry: InquiryRecord,
        transcript: str,
        call_summary: str,
        recording_url: Optional[str]
    ) -> PostCallResult:
        """
        Run the post-call processing pipeline.

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

            # Initialize crew if needed
            if not self.post_call_crew:
                self.post_call_crew = PostCallCrew()

            # Run the crew
            result = self.post_call_crew.run(
                inquiry=inquiry,
                transcript=transcript,
                call_summary=call_summary,
                recording_url=recording_url
            )

            return result

        except Exception as e:
            logger.error(f"Post-call pipeline failed for {inquiry.id}: {e}")

            return PostCallResult(
                success=False,
                errors=[str(e)]
            )

    async def _update_post_call_results(
        self,
        inquiry_id: str,
        result: PostCallResult
    ) -> None:
        """
        Update database with post-call results.

        Args:
            inquiry_id: Inquiry ID
            result: Post-call crew result
        """
        try:
            # Update analysis
            if result.analysis:
                await db_service.update_call_analysis(
                    inquiry_id,
                    result.analysis.model_dump()
                )

            # Update based on outcome
            if result.proposal_pdf_path or result.meeting_booked:
                # Hot lead processed
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
        """
        Get full inquiry status for debugging.

        Args:
            inquiry_id: Inquiry ID

        Returns:
            Full inquiry record
        """
        return await db_service.get_inquiry(inquiry_id)


# ===========================================
# Singleton Instance
# ===========================================

lead_processor = LeadProcessor()
