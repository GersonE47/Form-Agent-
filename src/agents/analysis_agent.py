"""Analysis Agent for post-call transcript analysis."""

import logging
from typing import Optional
from crewai import Agent, Task

from src.models import CallAnalysis, InquiryRecord

logger = logging.getLogger(__name__)


class AnalysisAgentFactory:
    """
    Factory for creating the Analysis Agent.

    The Analysis Agent processes call transcripts to extract
    actionable insights and determine next steps.
    """

    @staticmethod
    def create() -> Agent:
        """
        Create an Analysis Agent for post-call processing.

        Returns:
            Configured CrewAI Agent for call analysis
        """
        return Agent(
            role="Sales Call Analyst",
            goal="""Analyze call transcripts to extract actionable insights,
            determine prospect interest level, identify next steps, and
            provide clear recommendations for follow-up. Your analysis
            directly drives the automated follow-up process.""",
            backstory="""You are a sales operations analyst who has reviewed
            thousands of sales calls across industries. You have developed
            an expert ability to identify buying signals, objections, and
            commitment levels from conversation patterns.

            Your analysis expertise includes:
            - Identifying explicit and implicit buying signals
            - Recognizing objections and their underlying concerns
            - Assessing commitment level and next steps
            - Detecting when meetings are agreed upon
            - Parsing natural language time references
            - Evaluating overall interest and engagement

            You provide clear, actionable recommendations that can be
            automated. Your analysis is:
            - Objective and evidence-based
            - Focused on actionable outcomes
            - Clear about uncertainty
            - Consistent in scoring methodology

            When you identify a meeting time mentioned in conversation,
            you always extract it precisely for calendar booking.""",
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
        """
        Create an analysis task for a call transcript.

        Args:
            agent: The Analysis Agent
            transcript: Full call transcript
            call_summary: Optional summary from Retell
            inquiry: Original inquiry record with context

        Returns:
            Configured Task for analysis
        """
        # Build context
        context = ""
        if inquiry:
            context = f"""
        **PRE-CALL CONTEXT:**
        - Company: {inquiry.company_name}
        - Original Lead Score: {inquiry.lead_score or 'Not scored'}
        - Lead Category: {inquiry.lead_category or 'Unknown'}
        - Primary Goal: {inquiry.primary_goal or 'Not specified'}
        - Business Challenges: {inquiry.business_challenges or 'Not specified'}
        - Timeline: {inquiry.timeline or 'Not specified'}
            """

        retell_summary = ""
        if call_summary:
            retell_summary = f"""
        **RETELL CALL SUMMARY:**
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

        **ANALYZE THE FOLLOWING:**

        1. **CALL SUMMARY** (3-5 sentences)
           Provide a brief, objective summary of what was discussed:
           - Main topics covered
           - Key points the prospect made
           - How the conversation flowed
           - Final outcome/conclusion

        2. **SENTIMENT**
           Rate the overall prospect sentiment:
           - "positive": Engaged, enthusiastic, receptive
           - "neutral": Professional but reserved, asking questions
           - "negative": Resistant, dismissive, objecting frequently

        3. **INTEREST LEVEL** (0-100)
           Score based on engagement signals:
           - 80-100: Very interested, asking detailed questions, discussing next steps
           - 60-79: Interested, engaged in conversation, some positive signals
           - 40-59: Moderate interest, listening but reserved
           - 20-39: Low interest, short responses, some objections
           - 0-19: Not interested, trying to end call, strong objections

        4. **KEY PAIN POINTS** (List)
           Specific challenges the prospect mentioned during the call.
           Only include points they explicitly stated or strongly implied.

        5. **OBJECTIONS RAISED** (List)
           Any hesitations, concerns, or objections they expressed.
           Include both explicit objections and implicit concerns.

        6. **BUYING SIGNALS** (List)
           Positive indicators of purchase intent:
           - Asking about pricing or timeline
           - Discussing implementation details
           - Mentioning stakeholders to involve
           - Expressing urgency
           - Comparing to alternatives

        7. **NEXT STEPS DISCUSSED** (List)
           Any follow-up actions mentioned by either party:
           - Meetings to schedule
           - Information to send
           - People to involve
           - Decisions to make

        8. **MEETING AGREED** (true/false)
           Did the prospect agree to a follow-up meeting?
           Only mark true if there was clear agreement.

        9. **PROPOSED MEETING TIME** (if applicable)
           If a meeting time was discussed, extract it:
           - Look for explicit times: "Wednesday at 3pm", "next Tuesday"
           - Look for relative times: "tomorrow", "end of week"
           - Provide the most recent/final agreed time
           - Format: Natural language is fine (e.g., "Wednesday at 3pm")

        10. **BUDGET/TIMELINE/AUTHORITY CONFIRMATION**
            - budget_confirmed: Was budget discussed? (true/false/null)
            - timeline_confirmed: Was timeline confirmed? (true/false/null)
            - decision_maker_confirmed: Are they the decision maker? (true/false/null)

        11. **RECOMMENDED ACTION** (1-2 sentences)
            What should happen next based on this call:
            - For high interest: Specific follow-up action
            - For medium interest: Nurturing approach
            - For low interest: Appropriate next step

        12. **UPDATED LEAD SCORE** (0-100)
            Based on the call, what should the new lead score be?
            Consider: Did interest increase or decrease from pre-call score?

        **Output Format:**
        Provide a JSON object matching the CallAnalysis schema with all fields populated.
        """

        return Task(
            description=description,
            expected_output="Structured JSON object with call analysis matching CallAnalysis schema",
            agent=agent,
            output_pydantic=CallAnalysis
        )


def create_analysis_agent() -> Agent:
    """Convenience function to create an Analysis Agent."""
    return AnalysisAgentFactory.create()
