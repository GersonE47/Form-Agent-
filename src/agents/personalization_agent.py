"""Personalization Agent for call strategy creation."""

import logging
from typing import Optional
from crewai import Agent, Task

from src.models import (
    PersonalizationContext,
    ParsedLead,
    CompanyResearch,
    LeadScoring
)

logger = logging.getLogger(__name__)


class PersonalizationAgentFactory:
    """
    Factory for creating the Personalization Agent.

    The Personalization Agent creates custom talking points
    and call strategies for the AI voice agent.
    """

    @staticmethod
    def create() -> Agent:
        """
        Create a Personalization Agent for call strategy.

        Returns:
            Configured CrewAI Agent for personalization
        """
        return Agent(
            role="Sales Conversation Strategist",
            goal="""Create personalized call scripts and talking points that resonate
            with each prospect's specific situation and needs. Your content will be
            used by an AI voice agent to conduct discovery calls, so it must be
            natural, conversational, and adaptable.""",
            backstory="""You are a master sales strategist who has coached hundreds
            of sales representatives at top tech companies. You understand that
            every prospect is unique and generic pitches fail.

            Your personalization philosophy:
            - Lead with the prospect's specific pain points, not features
            - Reference their industry context to build credibility
            - Anticipate objections before they arise
            - Create natural conversation flow, not rigid scripts
            - Build rapport through relevant, specific references

            You craft talking points that feel authentic and help the AI voice
            agent build genuine connections. Your content is:
            - Concise and conversational (voice-friendly)
            - Specific to their situation
            - Focused on discovery, not selling
            - Prepared for common objections

            You know that the best sales conversations are two-way dialogues
            focused on understanding the prospect's needs.""",
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
        """
        Create a personalization task for a specific lead.

        Args:
            agent: The Personalization Agent
            lead: Parsed lead data
            research: Research findings from Research Agent
            scoring: Scoring results from Scoring Agent

        Returns:
            Configured Task for personalization
        """
        # Build context sections
        research_context = ""
        if research:
            research_context = f"""
        **Research Insights:**
        - Industry: {research.industry}
        - Company Size: {research.company_size_estimate or 'Unknown'}
        - Summary: {research.company_summary}
        - Pain Points: {', '.join(research.pain_points[:3]) if research.pain_points else 'None identified'}
        - AI Opportunities: {', '.join(research.ai_opportunities[:3]) if research.ai_opportunities else 'None identified'}
        - Tech Stack: {', '.join(research.tech_stack[:5]) if research.tech_stack else 'Unknown'}
            """

        scoring_context = ""
        if scoring:
            scoring_context = f"""
        **Lead Score:** {scoring.total_score}/100 ({scoring.category.value.upper()})
        - Budget signals: {scoring.budget_score}/25
        - Timeline urgency: {scoring.timeline_score}/25
        - ICP fit: {scoring.fit_score}/25
        - Engagement: {scoring.engagement_score}/25
        - Notes: {scoring.priority_notes or 'None'}
            """

        description = f"""
        Create a personalized call strategy for the AI voice agent calling {lead.company_name}.

        **PROSPECT INFORMATION:**
        - Company: {lead.company_name}
        - Contact Email: {lead.email}
        - Website: {lead.website or 'Not provided'}
        - Primary Goal: {lead.primary_goal or 'Not specified'}
        - Business Challenges: {lead.business_challenges or 'Not specified'}
        - Data Sources: {lead.data_sources or 'Not specified'}
        - Timeline: {lead.timeline or 'Not specified'}

        {research_context}

        {scoring_context}

        **CREATE THE FOLLOWING:**

        1. **CUSTOM OPENER** (2-3 conversational sentences)
           Create a personalized opener that:
           - Thanks them for their interest
           - References something specific about their company or industry
           - Transitions naturally to discovery
           - Sounds natural when spoken aloud

           Example format: "Thanks for reaching out, [Name]. I saw that [specific reference].
           I'd love to learn more about what prompted your interest in AI solutions."

        2. **PAIN POINT REFERENCE** (2-3 sentences)
           How to naturally bring up their stated challenges:
           - Connect their challenge to AI solutions
           - Show understanding without being presumptuous
           - Invite them to elaborate

           Example: "You mentioned [challenge]. We've helped companies tackle similar
           issues with [brief approach]. Tell me more about how this impacts your operations."

        3. **VALUE PROPOSITION** (2-3 sentences)
           A tailored value statement for their specific situation:
           - Address their stated goal
           - Reference relevant capabilities
           - Keep it benefit-focused, not feature-focused

        4. **SUGGESTED QUESTIONS** (5 questions)
           Discovery questions tailored to their situation:
           - Start broad, then get specific
           - Uncover budget, timeline, decision process
           - Understand their current state and desired state
           - Questions should flow naturally in conversation

        5. **OBJECTION HANDLERS** (Provide handlers for these common objections)
           Prepare natural responses for:

           a) "We're not ready yet"
           b) "We're exploring other options"
           c) "Budget is tight"
           d) "Need to talk to my team"

           Each handler should:
           - Acknowledge their concern
           - Provide a gentle reframe
           - Keep the conversation open

        6. **CALL STRATEGY** (2-3 sentences)
           Overall approach recommendation based on their score and profile:
           - For HOT leads: Focus on timeline and next steps
           - For WARM leads: Focus on education and value demonstration
           - For NURTURE leads: Focus on understanding and qualification

           Include specific guidance on pacing and tone.

        **IMPORTANT GUIDELINES:**
        - All content must sound natural when spoken aloud
        - Avoid jargon unless it's relevant to their industry
        - Keep sentences short and conversational
        - Focus on discovery, not pitching
        - Be confident but not pushy

        **Output Format:**
        Provide a JSON object with:
        - custom_opener: The personalized opening
        - pain_point_reference: How to reference their challenges
        - value_proposition: Tailored value statement
        - talking_points: List of key points to cover
        - suggested_questions: List of 5 discovery questions
        - objection_handlers: Dict with objection -> response mappings
        - call_strategy: Overall approach recommendation
        """

        return Task(
            description=description,
            expected_output="Structured JSON object with call personalization strategy matching PersonalizationContext schema",
            agent=agent,
            output_pydantic=PersonalizationContext
        )


def create_personalization_agent() -> Agent:
    """Convenience function to create a Personalization Agent."""
    return PersonalizationAgentFactory.create()
