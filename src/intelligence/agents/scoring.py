"""Scoring Agent for lead qualification."""

import logging
from typing import Optional
from crewai import Agent, Task

from src.models import ParsedLead, CompanyResearch, LeadScoring, LeadCategory

logger = logging.getLogger(__name__)


class ScoringAgentFactory:
    """Factory for creating Scoring Agent."""

    @staticmethod
    def create() -> Agent:
        """Create a Scoring Agent for lead qualification."""
        return Agent(
            role="Lead Qualification Specialist",
            goal="""Score and categorize leads based on BANT criteria
            (Budget, Authority, Need, Timeline) to prioritize sales efforts.""",
            backstory="""You are a sales operations expert who has developed
            and refined lead scoring models for high-growth B2B companies.

            Your scoring methodology:
            - Budget (0-25): Signs of investment capability and willingness
            - Timeline (0-25): Urgency and readiness to move forward
            - Fit (0-25): Match between their needs and AI solutions
            - Engagement (0-25): Level of detail and seriousness in inquiry

            You look for both explicit signals (stated budget, timeline) and
            implicit signals (company size, urgency in language, specificity
            of requirements).

            You categorize leads as:
            - HOT (70-100): Ready to buy, clear budget and timeline
            - WARM (40-69): Interested, needs nurturing
            - NURTURE (<40): Early stage, educational content needed""",
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
        """Create a scoring task."""
        research_context = ""
        if research:
            research_context = f"""
        **Research Findings:**
        - Industry: {research.industry}
        - Company Size: {research.company_size_estimate or 'Unknown'}
        - Summary: {research.company_summary}
        - Pain Points: {', '.join(research.pain_points[:3]) if research.pain_points else 'None identified'}
        - AI Opportunities: {', '.join(research.ai_opportunities[:3]) if research.ai_opportunities else 'None identified'}
        - Research Confidence: {research.research_confidence}
            """

        description = f"""
        Score and categorize this lead based on qualification criteria.

        **Lead Information:**
        - Company: {lead.company_name}
        - Email: {lead.email}
        - Website: {lead.website or 'Not provided'}
        - Primary Goal: {lead.primary_goal or 'Not specified'}
        - Business Challenges: {lead.business_challenges or 'Not specified'}
        - Data Sources: {lead.data_sources or 'Not specified'}
        - Infrastructure Criticality: {lead.infrastructure_criticality or 'Not specified'}/5
        - Timeline: {lead.timeline or 'Not specified'}
        - Preferred Contact Time: {lead.preferred_datetime or 'Not specified'}

        {research_context}

        **Scoring Criteria (0-25 each, total 0-100):**

        1. **Budget Score (0-25)**
           - Infrastructure criticality 4-5 suggests higher investment tolerance (+5-10)
           - Specific data sources mentioned indicates readiness (+5)
           - Enterprise email domain vs. generic (+3)
           - Company size from research (+2-5)

        2. **Timeline Score (0-25)**
           - Specific timeline mentioned: immediate/urgent (+20-25), 3-6 months (+15), exploring (+5-10)
           - Preferred contact time provided shows engagement (+3)
           - Urgency language in challenges (+5)

        3. **Fit Score (0-25)**
           - Clear AI use case in primary goal (+10-15)
           - Specific business challenges that AI can address (+5-10)
           - Relevant data sources available (+5)
           - Industry match with AI solutions (+5)

        4. **Engagement Score (0-25)**
           - Detailed business challenges (+10)
           - Multiple form fields completed (+5)
           - Specific questions or requirements (+5)
           - Professional email domain (+3)

        **Categorization:**
        - HOT (70-100): Immediate follow-up, proposal ready
        - WARM (40-69): Nurture with case studies, schedule call
        - NURTURE (<40): Educational content, long-term nurture

        **Output:**
        Provide scoring with clear rationale for each component.
        """

        return Task(
            description=description,
            expected_output="Structured JSON matching LeadScoring schema with rationale",
            agent=agent,
            output_pydantic=LeadScoring
        )
