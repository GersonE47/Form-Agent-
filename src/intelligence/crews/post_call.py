"""Post-Call Crew - Orchestrates post-call analysis and actions with async support."""

import logging
import asyncio
from typing import Optional
from datetime import datetime
from crewai import Crew, Process

from src.intelligence.agents.analysis import AnalysisAgentFactory
from src.intelligence.agents.proposal import ProposalAgentFactory
from src.core.config import get_settings
from src.models import (
    InquiryRecord,
    CallAnalysis,
    ProposalContent,
    PostCallResult,
    CallSentiment
)
from src.integrations.calendar import calendar_service
from src.integrations.email import email_service
from src.integrations.pdf import pdf_generator

logger = logging.getLogger(__name__)


class PostCallCrew:
    """
    Post-Call Processing Crew with async support.

    Orchestrates:
    1. Analysis Agent - Parse transcript for insights
    2. Routing Logic - Determine follow-up based on interest
    3. Proposal Agent - Generate proposal for hot leads
    4. Calendar booking and email sending

    Uses asyncio.to_thread() for blocking operations.
    """

    def __init__(self):
        """Initialize agents."""
        self.analysis_agent = AnalysisAgentFactory.create()
        self.proposal_agent = ProposalAgentFactory.create()
        self.settings = get_settings()
        logger.info("Post-call crew initialized")

    async def run_async(
        self,
        inquiry: InquiryRecord,
        transcript: str,
        call_summary: Optional[str] = None,
        recording_url: Optional[str] = None
    ) -> PostCallResult:
        """
        Execute post-call processing asynchronously.

        Args:
            inquiry: Original inquiry record
            transcript: Call transcript
            call_summary: Optional summary from Retell
            recording_url: Optional recording URL

        Returns:
            PostCallResult with all outcomes
        """
        logger.info(f"Starting async post-call crew for {inquiry.company_name}")

        # Run synchronous crew in thread pool
        return await asyncio.to_thread(
            self.run,
            inquiry,
            transcript,
            call_summary,
            recording_url
        )

    def run(
        self,
        inquiry: InquiryRecord,
        transcript: str,
        call_summary: Optional[str] = None,
        recording_url: Optional[str] = None
    ) -> PostCallResult:
        """
        Execute post-call processing (synchronous).

        For async contexts, use run_async() instead.

        Args:
            inquiry: Original inquiry record
            transcript: Call transcript
            call_summary: Optional summary from Retell
            recording_url: Optional recording URL

        Returns:
            PostCallResult with all outcomes
        """
        logger.info(f"Starting post-call crew for {inquiry.company_name}")

        result = PostCallResult(success=True)

        # Step 1: Run Analysis Agent
        analysis = self._run_analysis(inquiry, transcript, call_summary, result)

        if not analysis:
            logger.error("Analysis failed - cannot proceed")
            result.success = False
            return result

        result.analysis = analysis

        # Step 2: Route based on interest level
        logger.info(
            f"Analysis complete - Interest: {analysis.interest_level}, "
            f"Meeting agreed: {analysis.meeting_agreed}"
        )

        if analysis.interest_level >= self.settings.HOT_THRESHOLD:
            self._process_hot_lead(inquiry, analysis, result)
        elif analysis.interest_level >= self.settings.WARM_THRESHOLD:
            self._process_warm_lead(inquiry, analysis, result)
        else:
            self._process_nurture_lead(inquiry, analysis, result)

        logger.info(
            f"Post-call crew completed - "
            f"Email sent: {result.email_sent}, Meeting booked: {result.meeting_booked}"
        )

        return result

    def _run_analysis(
        self,
        inquiry: InquiryRecord,
        transcript: str,
        call_summary: Optional[str],
        result: PostCallResult
    ) -> Optional[CallAnalysis]:
        """Run the Analysis Agent."""
        try:
            logger.info(f"Running Analysis Agent for {inquiry.company_name}")

            task = AnalysisAgentFactory.create_analysis_task(
                self.analysis_agent,
                transcript,
                call_summary,
                inquiry
            )

            crew = Crew(
                agents=[self.analysis_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True,
                memory=True
            )

            crew.kickoff()

            if task.output and task.output.pydantic:
                analysis = task.output.pydantic
                logger.info(f"Analysis completed - Interest: {analysis.interest_level}")
                return analysis
            else:
                logger.warning("Analysis returned no output")
                result.errors.append("Analysis returned no output")
                return self._get_fallback_analysis(transcript, call_summary)

        except Exception as e:
            logger.error(f"Analysis Agent failed: {e}")
            result.errors.append(f"Analysis failed: {str(e)}")
            return self._get_fallback_analysis(transcript, call_summary)

    def _process_hot_lead(
        self,
        inquiry: InquiryRecord,
        analysis: CallAnalysis,
        result: PostCallResult
    ):
        """Process a hot lead with proposal, meeting, and email."""
        logger.info(f"Processing HOT lead: {inquiry.company_name}")

        # Step 1: Generate proposal
        proposal = self._generate_proposal(inquiry, analysis, result)

        if proposal:
            result.proposal = proposal
            pdf_path = pdf_generator.markdown_to_pdf(
                proposal.markdown_content,
                inquiry.company_name
            )
            result.proposal_pdf_path = pdf_path
            logger.info(f"Proposal PDF generated: {pdf_path}")

        # Step 2: Book meeting if agreed
        meeting_link = None
        if analysis.meeting_agreed and analysis.proposed_meeting_time:
            meeting_link = self._book_meeting(inquiry, analysis, result)

        # Step 3: Send email with proposal
        email_sent = email_service.send_hot_lead_email(
            to_email=inquiry.email,
            company_name=inquiry.company_name,
            contact_name=inquiry.company_name,
            meeting_link=meeting_link,
            proposal_path=result.proposal_pdf_path
        )

        result.email_sent = email_sent
        if not email_sent:
            result.errors.append("Failed to send hot lead email")

    def _process_warm_lead(
        self,
        inquiry: InquiryRecord,
        analysis: CallAnalysis,
        result: PostCallResult
    ):
        """Process a warm lead with case study email."""
        logger.info(f"Processing WARM lead: {inquiry.company_name}")

        email_sent = email_service.send_warm_lead_email(
            to_email=inquiry.email,
            company_name=inquiry.company_name,
            contact_name=inquiry.company_name,
            case_study_link="https://nodari.ai/case-studies"
        )

        result.email_sent = email_sent
        if not email_sent:
            result.errors.append("Failed to send warm lead email")

    def _process_nurture_lead(
        self,
        inquiry: InquiryRecord,
        analysis: CallAnalysis,
        result: PostCallResult
    ):
        """Process a nurture lead with educational content."""
        logger.info(f"Processing NURTURE lead: {inquiry.company_name}")

        email_sent = email_service.send_nurture_email(
            to_email=inquiry.email,
            contact_name=inquiry.company_name
        )

        result.email_sent = email_sent
        if not email_sent:
            result.errors.append("Failed to send nurture email")

    def _generate_proposal(
        self,
        inquiry: InquiryRecord,
        analysis: CallAnalysis,
        result: PostCallResult
    ) -> Optional[ProposalContent]:
        """Generate proposal using Proposal Agent."""
        try:
            logger.info(f"Generating proposal for {inquiry.company_name}")

            task = ProposalAgentFactory.create_proposal_task(
                self.proposal_agent,
                inquiry,
                analysis
            )

            crew = Crew(
                agents=[self.proposal_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True,
                memory=True
            )

            crew.kickoff()

            if task.output and task.output.pydantic:
                proposal = task.output.pydantic
                logger.info("Proposal generated successfully")
                return proposal
            else:
                logger.warning("Proposal returned no output")
                result.errors.append("Proposal generation returned no output")
                return None

        except Exception as e:
            logger.error(f"Proposal Agent failed: {e}")
            result.errors.append(f"Proposal failed: {str(e)}")
            return None

    def _book_meeting(
        self,
        inquiry: InquiryRecord,
        analysis: CallAnalysis,
        result: PostCallResult
    ) -> Optional[str]:
        """Book a calendar meeting."""
        try:
            if not calendar_service.is_available():
                logger.warning("Calendar service not available")
                result.errors.append("Calendar service not configured")
                return None

            meeting_time = None
            if analysis.proposed_meeting_time:
                meeting_time = calendar_service.parse_meeting_time(
                    analysis.proposed_meeting_time
                )

            if not meeting_time:
                logger.info("Finding next available slot")
                meeting_time = calendar_service.find_available_slot(datetime.now())

            if not meeting_time:
                logger.warning("No available meeting slots")
                result.errors.append("No available meeting slots")
                return None

            meeting_link = calendar_service.create_meeting(
                attendee_email=inquiry.email,
                company_name=inquiry.company_name,
                meeting_time=meeting_time
            )

            if meeting_link:
                result.meeting_booked = True
                result.meeting_link = meeting_link
                logger.info(f"Meeting booked: {meeting_link}")
                return meeting_link
            else:
                result.errors.append("Failed to create calendar event")
                return None

        except Exception as e:
            logger.error(f"Meeting booking failed: {e}")
            result.errors.append(f"Meeting booking failed: {str(e)}")
            return None

    def _get_fallback_analysis(
        self,
        transcript: str,
        call_summary: Optional[str]
    ) -> CallAnalysis:
        """Create fallback analysis when agent fails."""
        summary = call_summary or f"Call transcript ({len(transcript)} chars)"

        return CallAnalysis(
            call_summary=summary[:500],
            sentiment=CallSentiment.NEUTRAL,
            interest_level=50,
            key_pain_points=[],
            objections_raised=[],
            buying_signals=[],
            next_steps_discussed=[],
            meeting_agreed=False,
            proposed_meeting_time=None,
            budget_confirmed=None,
            timeline_confirmed=None,
            decision_maker_confirmed=None,
            recommended_action="Manual review required - automated analysis failed",
            updated_lead_score=50
        )


async def run_post_call_crew_async(
    inquiry: InquiryRecord,
    transcript: str,
    call_summary: Optional[str] = None,
    recording_url: Optional[str] = None
) -> PostCallResult:
    """Convenience function to run post-call crew asynchronously."""
    crew = PostCallCrew()
    return await crew.run_async(inquiry, transcript, call_summary, recording_url)
