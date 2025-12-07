"""Pre-Call Crew - Orchestrates pre-call intelligence gathering."""

import logging
from typing import Optional, Dict, Any
from crewai import Crew, Process

from src.agents.research_agent import ResearchAgentFactory
from src.agents.scoring_agent import ScoringAgentFactory
from src.agents.personalization_agent import PersonalizationAgentFactory
from src.models import (
    ParsedLead,
    CompanyResearch,
    LeadScoring,
    PersonalizationContext,
    PreCallResult,
    LeadCategory
)

logger = logging.getLogger(__name__)


class PreCallCrew:
    """
    Pre-Call Intelligence Crew.

    Orchestrates the sequential execution of:
    1. Research Agent - Gather company intelligence
    2. Scoring Agent - Qualify and score the lead
    3. Personalization Agent - Create call strategy

    The output from each agent feeds into the next.
    """

    def __init__(self):
        """Initialize all agents."""
        self.research_agent = ResearchAgentFactory.create()
        self.scoring_agent = ScoringAgentFactory.create()
        self.personalization_agent = PersonalizationAgentFactory.create()

        logger.info("Pre-call crew initialized with all agents")

    def run(self, lead: ParsedLead) -> PreCallResult:
        """
        Execute the pre-call intelligence crew.

        Runs agents sequentially:
        1. Research → research_output
        2. Scoring (uses research) → scoring_output
        3. Personalization (uses both) → personalization_output

        Args:
            lead: Parsed lead data from form submission

        Returns:
            PreCallResult with all outputs and any errors
        """
        logger.info(f"Starting pre-call crew for {lead.company_name}")

        result = PreCallResult(success=True)

        # Step 1: Research Agent
        research = self._run_research(lead, result)

        # Step 2: Scoring Agent
        scoring = self._run_scoring(lead, research, result)

        # Step 3: Personalization Agent
        personalization = self._run_personalization(lead, research, scoring, result)

        # Log completion
        if result.success:
            logger.info(
                f"Pre-call crew completed for {lead.company_name} - "
                f"Score: {scoring.total_score if scoring else 'N/A'}, "
                f"Tier: {scoring.category.value if scoring else 'N/A'}"
            )
        else:
            logger.warning(
                f"Pre-call crew completed with errors for {lead.company_name}: "
                f"{result.errors}"
            )

        return result

    def _run_research(
        self,
        lead: ParsedLead,
        result: PreCallResult
    ) -> Optional[CompanyResearch]:
        """Run Research Agent with graceful degradation."""
        try:
            logger.info(f"Running Research Agent for {lead.company_name}")

            # Create the research task
            task = ResearchAgentFactory.create_research_task(
                self.research_agent,
                lead
            )

            # Create mini-crew for just this task
            crew = Crew(
                agents=[self.research_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True,
                memory=True
            )

            # Execute
            crew.kickoff()

            # Get output
            if task.output and task.output.pydantic:
                research = task.output.pydantic
                result.research = research
                logger.info(f"Research completed - Industry: {research.industry}")
                return research
            else:
                logger.warning("Research task returned no structured output")
                result.errors.append("Research returned no output")
                return self._get_fallback_research(lead)

        except Exception as e:
            logger.error(f"Research Agent failed: {e}")
            result.errors.append(f"Research failed: {str(e)}")
            return self._get_fallback_research(lead)

    def _run_scoring(
        self,
        lead: ParsedLead,
        research: Optional[CompanyResearch],
        result: PreCallResult
    ) -> Optional[LeadScoring]:
        """Run Scoring Agent with graceful degradation."""
        try:
            logger.info(f"Running Scoring Agent for {lead.company_name}")

            # Create the scoring task
            task = ScoringAgentFactory.create_scoring_task(
                self.scoring_agent,
                lead,
                research
            )

            # Create mini-crew
            crew = Crew(
                agents=[self.scoring_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True,
                memory=True
            )

            # Execute
            crew.kickoff()

            # Get output
            if task.output and task.output.pydantic:
                scoring = task.output.pydantic
                result.scoring = scoring
                logger.info(
                    f"Scoring completed - Score: {scoring.total_score}, "
                    f"Category: {scoring.category.value}"
                )
                return scoring
            else:
                logger.warning("Scoring task returned no structured output")
                result.errors.append("Scoring returned no output")
                return self._get_fallback_scoring(lead)

        except Exception as e:
            logger.error(f"Scoring Agent failed: {e}")
            result.errors.append(f"Scoring failed: {str(e)}")
            return self._get_fallback_scoring(lead)

    def _run_personalization(
        self,
        lead: ParsedLead,
        research: Optional[CompanyResearch],
        scoring: Optional[LeadScoring],
        result: PreCallResult
    ) -> Optional[PersonalizationContext]:
        """Run Personalization Agent with graceful degradation."""
        try:
            logger.info(f"Running Personalization Agent for {lead.company_name}")

            # Create the personalization task
            task = PersonalizationAgentFactory.create_personalization_task(
                self.personalization_agent,
                lead,
                research,
                scoring
            )

            # Create mini-crew
            crew = Crew(
                agents=[self.personalization_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True,
                memory=True
            )

            # Execute
            crew.kickoff()

            # Get output
            if task.output and task.output.pydantic:
                personalization = task.output.pydantic
                result.personalization = personalization
                logger.info("Personalization completed")
                return personalization
            else:
                logger.warning("Personalization task returned no structured output")
                result.errors.append("Personalization returned no output")
                return self._get_fallback_personalization(lead)

        except Exception as e:
            logger.error(f"Personalization Agent failed: {e}")
            result.errors.append(f"Personalization failed: {str(e)}")
            return self._get_fallback_personalization(lead)

    def _get_fallback_research(self, lead: ParsedLead) -> CompanyResearch:
        """Create minimal research when agent fails."""
        return CompanyResearch(
            company_summary=f"Company: {lead.company_name}. Website: {lead.website or 'Unknown'}",
            industry="Unknown",
            company_size_estimate=None,
            tech_stack=[],
            recent_news=[],
            pain_points=[lead.business_challenges] if lead.business_challenges else [],
            ai_opportunities=[lead.primary_goal] if lead.primary_goal else [],
            competitors=[],
            research_confidence=0.0
        )

    def _get_fallback_scoring(self, lead: ParsedLead) -> LeadScoring:
        """Create default scoring when agent fails."""
        # Basic scoring based on available data
        budget_score = (lead.infrastructure_criticality or 3) * 5  # 5-25
        timeline_score = 15 if lead.timeline else 8
        fit_score = 15 if lead.primary_goal else 10
        engagement_score = 15 if lead.business_challenges else 10

        total = budget_score + timeline_score + fit_score + engagement_score

        # Determine category
        if total >= 70:
            category = LeadCategory.HOT
        elif total >= 40:
            category = LeadCategory.WARM
        else:
            category = LeadCategory.NURTURE

        return LeadScoring(
            total_score=total,
            category=category,
            budget_score=budget_score,
            timeline_score=timeline_score,
            fit_score=fit_score,
            engagement_score=engagement_score,
            scoring_rationale="Fallback scoring based on form data only - AI scoring failed",
            priority_notes="Manual review recommended"
        )

    def _get_fallback_personalization(
        self,
        lead: ParsedLead
    ) -> PersonalizationContext:
        """Create minimal personalization when agent fails."""
        return PersonalizationContext(
            custom_opener=f"Thank you for your interest in Nodari AI, {lead.company_name}. "
                         f"I'd love to learn more about your AI initiatives.",
            pain_point_reference=f"You mentioned interest in {lead.primary_goal or 'AI solutions'}. "
                                 f"Tell me more about what prompted that.",
            value_proposition="At Nodari AI, we help companies implement custom AI solutions "
                            "that drive real business results.",
            talking_points=[
                "Understand their specific use case",
                "Discuss timeline and priorities",
                "Identify decision makers",
                "Explore budget considerations"
            ],
            suggested_questions=[
                "What's driving your interest in AI right now?",
                "What would success look like for this project?",
                "Who else is involved in this decision?",
                "What's your ideal timeline?",
                "Have you worked with AI solutions before?"
            ],
            objection_handlers={
                "We're not ready yet": "I understand. Many companies start with a discovery "
                                       "conversation to understand what's possible. No commitment needed.",
                "Budget is tight": "That's common. We can discuss options that fit different "
                                  "investment levels, or start with a pilot.",
                "We're exploring other options": "That makes sense. I'd love to understand "
                                                 "what you're looking for so I can share how we differ.",
                "Need to talk to my team": "Absolutely. Would it help if I sent over some "
                                          "information you could share with them?"
            },
            call_strategy="Focus on discovery and understanding their needs. "
                         "Build rapport and identify next steps."
        )


def run_pre_call_crew(lead: ParsedLead) -> PreCallResult:
    """Convenience function to run pre-call crew."""
    crew = PreCallCrew()
    return crew.run(lead)
