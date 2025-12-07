"""Scoring Agent for lead qualification."""

import logging
from typing import Optional
from crewai import Agent, Task

from src.config import get_settings
from src.models import LeadScoring, LeadCategory, ParsedLead, CompanyResearch

logger = logging.getLogger(__name__)


class ScoringAgentFactory:
    """
    Factory for creating the Scoring Agent.

    The Scoring Agent qualifies leads using BANT framework
    (Budget, Authority, Need, Timeline) and behavioral signals.
    """

    @staticmethod
    def create() -> Agent:
        """
        Create a Scoring Agent for lead qualification.

        Returns:
            Configured CrewAI Agent for lead scoring
        """
        settings = get_settings()

        return Agent(
            role="Lead Qualification Specialist",
            goal=f"""Score and categorize leads based on their fit, intent, and
            readiness to purchase custom AI solutions. Use data-driven criteria
            to classify leads as:
            - HOT ({settings.HOT_THRESHOLD}+ points): Ready to buy, clear need
            - WARM ({settings.WARM_THRESHOLD}-{settings.HOT_THRESHOLD-1} points): Interested but needs nurturing
            - NURTURE (below {settings.WARM_THRESHOLD} points): Early stage, educational content needed""",
            backstory="""You are an expert in B2B sales qualification with deep
            experience in the AI/ML services industry. You use a modified BANT
            framework combined with behavioral signals to accurately predict
            deal potential.

            Your scoring methodology is:
            - Data-driven and consistent
            - Based on explicit signals from form data
            - Informed by research findings
            - Clear and explainable

            You understand that:
            - Explicit timeline statements indicate urgency
            - High infrastructure criticality scores suggest budget commitment
            - Detailed business challenges show genuine need
            - Quick follow-up requests indicate high intent
            - Company size and industry affect deal potential

            Your scoring directly influences sales prioritization, so accuracy
            is critical. You provide clear rationale for every score.""",
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    @staticmethod
    def create_scoring_task(
        agent: Agent,
        lead: ParsedLead,
        research: Optional[CompanyResearch] = None
    ) -> Task:
        """
        Create a scoring task for a specific lead.

        Args:
            agent: The Scoring Agent
            lead: Parsed lead data
            research: Optional research findings from Research Agent

        Returns:
            Configured Task for scoring
        """
        settings = get_settings()

        # Build research context
        research_context = ""
        if research:
            research_context = f"""
        **Research Findings:**
        - Industry: {research.industry}
        - Company Size: {research.company_size_estimate or 'Unknown'}
        - Summary: {research.company_summary}
        - Identified Pain Points: {', '.join(research.pain_points) or 'None identified'}
        - AI Opportunities: {', '.join(research.ai_opportunities) or 'None identified'}
        - Research Confidence: {research.research_confidence}
            """

        description = f"""
        Score this lead using our qualification criteria. Each component is worth 0-25 points.

        **LEAD DATA:**
        - Company: {lead.company_name}
        - Email: {lead.email}
        - Website: {lead.website or 'Not provided'}
        - Primary Goal: {lead.primary_goal or 'Not specified'}
        - Business Challenges: {lead.business_challenges or 'Not specified'}
        - Data Sources: {lead.data_sources or 'Not specified'}
        - Infrastructure Criticality (1-5 scale): {lead.infrastructure_criticality or 'Not specified'}
        - Timeline: {lead.timeline or 'Not specified'}
        - Preferred Meeting Time: {lead.preferred_datetime or 'Not specified'}

        {research_context}

        **SCORING CRITERIA:**

        1. **BUDGET SCORE (0-25 points)** - Budget/investment signals
           Based on infrastructure criticality rating:
           - Criticality 5 = 25 points (Mission critical, high investment)
           - Criticality 4 = 20 points
           - Criticality 3 = 15 points
           - Criticality 2 = 10 points
           - Criticality 1 = 5 points
           - Not specified = 10 points (neutral)

           Bonus considerations:
           - Large company size from research = +3
           - Tech-forward industry = +2

        2. **TIMELINE SCORE (0-25 points)** - Urgency signals
           Based on stated timeline:
           - "Immediately" / "ASAP" / "This month" = 25 points
           - "This quarter" / "Next 3 months" = 20 points
           - "Next 6 months" = 15 points
           - "Next year" = 10 points
           - "Exploring" / "No timeline" = 5 points
           - Not specified = 8 points

           Bonus: Specific meeting time provided = +3

        3. **FIT SCORE (0-25 points)** - ICP and use case match
           - Clear AI use case + existing data mentioned = 25 points
           - Clear use case, data unclear = 20 points
           - General interest, some specifics = 15 points
           - Vague requirements = 10 points
           - No clear fit = 5 points

           Consider: How well does their stated goal align with AI solutions?

        4. **ENGAGEMENT SCORE (0-25 points)** - Form engagement quality
           - Detailed responses + specific meeting time = 25 points
           - Detailed responses, flexible on meeting = 20 points
           - Brief but specific responses = 15 points
           - Minimal information provided = 10 points
           - Very sparse responses = 5 points

           Look at: Length and quality of challenge description

        **CLASSIFICATION:**
        - Total 70-100 points = HOT (prioritize immediately)
        - Total 40-69 points = WARM (nurture with content)
        - Total 0-39 points = NURTURE (educational sequence)

        **Output Format:**
        Provide a JSON object with:
        - total_score: Sum of all component scores (0-100)
        - category: "hot", "warm", or "nurture"
        - budget_score: Score for budget signals (0-25)
        - timeline_score: Score for urgency (0-25)
        - fit_score: Score for ICP fit (0-25)
        - engagement_score: Score for form engagement (0-25)
        - scoring_rationale: Detailed explanation of your scoring decisions
        - priority_notes: Any special considerations for sales team
        """

        return Task(
            description=description,
            expected_output="Structured JSON object with lead score and categorization matching LeadScoring schema",
            agent=agent,
            output_pydantic=LeadScoring
        )


def create_scoring_agent() -> Agent:
    """Convenience function to create a Scoring Agent."""
    return ScoringAgentFactory.create()
