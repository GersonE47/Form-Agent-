"""Proposal Agent for generating customized proposals."""

import logging
from typing import Optional
from crewai import Agent, Task
from crewai.tools import tool

from src.models import ProposalContent, InquiryRecord, CallAnalysis
from src.integrations.pdf import pdf_generator

logger = logging.getLogger(__name__)


class ProposalAgentFactory:
    """Factory for creating Proposal Agent."""

    @staticmethod
    def create() -> Agent:
        """Create a Proposal Agent for proposal generation."""

        @tool("generate_pdf")
        def generate_pdf(markdown_content: str, company_name: str) -> str:
            """
            Convert markdown proposal to PDF.

            Args:
                markdown_content: Full proposal in markdown
                company_name: Company name for filename

            Returns:
                Path to generated PDF
            """
            result = pdf_generator.markdown_to_pdf(markdown_content, company_name)
            return result or "Failed to generate PDF"

        return Agent(
            role="AI Solutions Proposal Writer",
            goal="""Create compelling, personalized proposals that clearly
            articulate the value of custom AI solutions.""",
            backstory="""You are a senior solutions architect and technical writer
            who has crafted winning proposals for Fortune 500 companies.

            Your proposal philosophy:
            - Lead with their specific pain points
            - Clearly articulate the proposed solution
            - Provide realistic timelines
            - Include investment guidance without hard quotes
            - End with compelling next steps

            You write in a confident, consultative tone. Your proposals are:
            - Concise yet comprehensive
            - Specific to their situation
            - Professionally formatted
            - Action-oriented""",
            tools=[generate_pdf],
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    @staticmethod
    def create_proposal_task(
        agent: Agent,
        inquiry: InquiryRecord,
        analysis: Optional[CallAnalysis] = None
    ) -> Task:
        """Create a proposal generation task."""
        research_context = ""
        if inquiry.company_research:
            research = inquiry.company_research
            research_context = f"""
        **Company Research:**
        - Industry: {research.get('industry', 'Unknown')}
        - Size: {research.get('company_size_estimate', 'Unknown')}
        - Summary: {research.get('company_summary', 'Not available')}
        - Pain Points: {', '.join(research.get('pain_points', [])[:3]) or 'Not identified'}
            """

        call_context = ""
        if analysis:
            call_context = f"""
        **Call Insights:**
        - Summary: {analysis.call_summary}
        - Interest: {analysis.interest_level}/100
        - Pain Points: {', '.join(analysis.key_pain_points[:3]) if analysis.key_pain_points else 'None'}
        - Buying Signals: {', '.join(analysis.buying_signals[:3]) if analysis.buying_signals else 'None'}
            """

        description = f"""
        Create a compelling proposal for {inquiry.company_name}.

        **Company Information:**
        - Company: {inquiry.company_name}
        - Email: {inquiry.email}
        - Website: {inquiry.website or 'Not provided'}
        - Primary Goal: {inquiry.primary_goal or 'Not specified'}
        - Business Challenges: {inquiry.business_challenges or 'Not specified'}
        - Timeline: {inquiry.timeline or 'Not specified'}

        {research_context}

        {call_context}

        **Create Proposal Sections:**

        1. **Executive Summary** (2-3 paragraphs)
           Hook with understanding of their situation, introduce approach, highlight benefits.

        2. **Understanding Your Challenges**
           Reflect back their challenges, show industry understanding.

        3. **Proposed Solution** (2-3 paragraphs)
           Describe recommended AI approach, focus on outcomes.

        4. **Implementation Timeline**
           Phases: Discovery, Development, Testing, Deployment.

        5. **Investment**
           Range-based guidance, what's included.

        6. **Next Steps**
           Clear call-to-action.

        7. **Why Nodari AI** (1 paragraph)
           Brief credentials.

        **Output:**
        Provide JSON with all sections AND complete markdown_content.
        """

        return Task(
            description=description,
            expected_output="Structured JSON matching ProposalContent schema with markdown_content",
            agent=agent,
            output_pydantic=ProposalContent
        )
