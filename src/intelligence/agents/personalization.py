"""Personalization Agent for call strategy creation."""

import logging
from typing import Optional
from crewai import Agent, Task

from src.models import (
    ParsedLead,
    CompanyResearch,
    LeadScoring,
    PersonalizationContext
)

logger = logging.getLogger(__name__)


class PersonalizationAgentFactory:
    """Factory for creating Personalization Agent."""

    @staticmethod
    def create() -> Agent:
        """Create a Personalization Agent for call strategy."""
        return Agent(
            role="Sales Conversation Strategist",
            goal="""Create personalized call strategies that resonate with
            prospects and maximize conversion potential.""",
            backstory="""You are a master sales coach who has trained thousands
            of SDRs and AEs on consultative selling. You understand that every
            prospect is unique and generic pitches don't work.

            Your personalization approach:
            - Lead with their specific situation, not your product
            - Reference concrete details from their business
            - Anticipate objections based on their profile
            - Prepare discovery questions that uncover true needs
            - Create value propositions that speak to their goals

            You craft conversation strategies that feel natural and helpful,
            not salesy. The AI voice agent will use your guidance to have
            meaningful conversations.""",
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    @staticmethod
    def create_personalization_task(
        agent: Agent,
        lead: ParsedLead,
        research: Optional[CompanyResearch] = None,
        scoring: Optional[LeadScoring] = None
    ) -> Task:
        """Create a personalization task."""
        research_context = ""
        if research:
            research_context = f"""
        **Research Insights:**
        - Industry: {research.industry}
        - Summary: {research.company_summary}
        - Pain Points: {', '.join(research.pain_points[:3]) if research.pain_points else 'None identified'}
        - AI Opportunities: {', '.join(research.ai_opportunities[:3]) if research.ai_opportunities else 'None identified'}
        - Recent News: {', '.join(research.recent_news[:2]) if research.recent_news else 'None found'}
            """

        scoring_context = ""
        if scoring:
            scoring_context = f"""
        **Lead Qualification:**
        - Total Score: {scoring.total_score}/100
        - Category: {scoring.category.value}
        - Rationale: {scoring.scoring_rationale}
        - Priority Notes: {scoring.priority_notes or 'None'}
            """

        description = f"""
        Create a personalized call strategy for the AI voice agent.

        **Lead Information:**
        - Company: {lead.company_name}
        - Primary Goal: {lead.primary_goal or 'Not specified'}
        - Business Challenges: {lead.business_challenges or 'Not specified'}
        - Timeline: {lead.timeline or 'Not specified'}

        {research_context}

        {scoring_context}

        **Create the Following:**

        1. **Custom Opener** (1-2 sentences)
           - Thank them for their interest
           - Reference something specific about them
           - Set a collaborative tone
           - Should feel natural for voice

        2. **Pain Point Reference** (1-2 sentences)
           - Acknowledge their specific challenge
           - Show you understand their situation
           - Bridge to how you might help

        3. **Value Proposition** (2-3 sentences)
           - Tailored to their goals
           - Focus on outcomes, not features
           - Credibility without bragging

        4. **Talking Points** (3-5 bullet points)
           - Key topics to cover in the call
           - Discovery questions to ask
           - Value points to emphasize

        5. **Suggested Questions** (4-6 questions)
           - Open-ended discovery questions
           - Questions about their decision process
           - Questions to uncover timeline and budget
           - Questions to identify other stakeholders

        6. **Objection Handlers** (3-4 common objections)
           - "We're not ready yet"
           - "Budget is tight"
           - "Need to talk to my team"
           - Any industry-specific objections

        7. **Call Strategy** (2-3 sentences)
           - Overall approach for this call
           - What to prioritize
           - Desired outcome

        **Guidelines:**
        - Write for spoken conversation (natural, not formal)
        - Keep responses concise - this is for a phone call
        - Be consultative, not pushy
        - Focus on understanding their needs
        """

        return Task(
            description=description,
            expected_output="Structured JSON matching PersonalizationContext schema",
            agent=agent,
            output_pydantic=PersonalizationContext
        )
