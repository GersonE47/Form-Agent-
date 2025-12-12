"""Analysis Agent for post-call transcript analysis."""

import logging
from typing import Optional
from crewai import Agent, Task

from src.models import CallAnalysis, InquiryRecord

logger = logging.getLogger(__name__)


class AnalysisAgentFactory:
    """Factory for creating Analysis Agent."""

    @staticmethod
    def create() -> Agent:
        """Create an Analysis Agent for call analysis."""
        return Agent(
            role="Sales Call Analyst",
            goal="""Analyze call transcripts to extract actionable insights,
            determine prospect interest level, and provide clear next steps.""",
            backstory="""You are a sales operations analyst who has reviewed
            thousands of sales calls. You have expert ability to identify:
            - Buying signals (explicit and implicit)
            - Objections and their underlying concerns
            - Commitment levels and next steps
            - Meeting agreements and time references
            - Overall interest and engagement

            Your analysis is:
            - Objective and evidence-based
            - Focused on actionable outcomes
            - Clear about uncertainty
            - Consistent in scoring methodology""",
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    @staticmethod
    def create_analysis_task(
        agent: Agent,
        transcript: str,
        call_summary: Optional[str] = None,
        inquiry: Optional[InquiryRecord] = None
    ) -> Task:
        """Create an analysis task for call transcript."""
        context = ""
        if inquiry:
            context = f"""
        **Pre-Call Context:**
        - Company: {inquiry.company_name}
        - Original Score: {inquiry.lead_score or 'Not scored'}
        - Category: {inquiry.lead_category or 'Unknown'}
        - Primary Goal: {inquiry.primary_goal or 'Not specified'}
        - Business Challenges: {inquiry.business_challenges or 'Not specified'}
            """

        retell_summary = ""
        if call_summary:
            retell_summary = f"""
        **Retell Call Summary:**
        {call_summary}
            """

        description = f"""
        Analyze this sales call transcript and extract actionable insights.

        {context}

        {retell_summary}

        **CALL TRANSCRIPT:**
        ---
        {transcript}
        ---

        **Analyze the Following:**

        1. **Call Summary** (3-5 sentences)
           Brief, objective summary of what was discussed.

        2. **Sentiment** (positive/neutral/negative)
           Overall prospect sentiment based on tone and engagement.

        3. **Interest Level** (0-100)
           - 80-100: Very interested, detailed questions, discussing next steps
           - 60-79: Interested, engaged, some positive signals
           - 40-59: Moderate, listening but reserved
           - 20-39: Low interest, short responses
           - 0-19: Not interested, trying to end call

        4. **Key Pain Points** (list)
           Specific challenges mentioned during the call.

        5. **Objections Raised** (list)
           Any hesitations or concerns expressed.

        6. **Buying Signals** (list)
           Positive indicators: asking about pricing, timeline, implementation.

        7. **Next Steps Discussed** (list)
           Follow-up actions mentioned by either party.

        8. **Meeting Agreed** (true/false)
           Was a follow-up meeting clearly agreed upon?

        9. **Proposed Meeting Time** (if applicable)
           Extract any mentioned meeting time (e.g., "Thursday at 10am").

        10. **BANT Confirmation**
            - budget_confirmed: Was budget discussed? (true/false/null)
            - timeline_confirmed: Was timeline confirmed? (true/false/null)
            - decision_maker_confirmed: Are they the decision maker? (true/false/null)

        11. **Recommended Action** (1-2 sentences)
            What should happen next based on this call.

        12. **Updated Lead Score** (0-100)
            New score based on call outcome.
        """

        return Task(
            description=description,
            expected_output="Structured JSON matching CallAnalysis schema",
            agent=agent,
            output_pydantic=CallAnalysis
        )
