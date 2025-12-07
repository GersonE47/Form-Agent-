"""Proposal Agent for generating customized proposals."""

import logging
from typing import Optional
from crewai import Agent, Task
from crewai_tools import tool

from src.tools.proposal_generator import ProposalGenerator
from src.models import ProposalContent, InquiryRecord, CallAnalysis

logger = logging.getLogger(__name__)


class ProposalAgentFactory:
    """
    Factory for creating the Proposal Agent.

    The Proposal Agent generates customized proposals for
    hot leads based on their needs and the call outcome.
    """

    @staticmethod
    def create() -> Agent:
        """
        Create a Proposal Agent for proposal generation.

        Returns:
            Configured CrewAI Agent for proposals
        """
        # Initialize proposal generator
        generator = ProposalGenerator()

        @tool("generate_proposal_pdf")
        def create_pdf(markdown_content: str, company_name: str) -> str:
            """
            Convert a markdown proposal to PDF format.

            Use this tool after creating the proposal content to generate
            a professional PDF document.

            Args:
                markdown_content: The full proposal in markdown format
                company_name: Company name for the filename

            Returns:
                File path to the generated PDF
            """
            return generator.markdown_to_pdf(markdown_content, company_name)

        return Agent(
            role="AI Solutions Proposal Writer",
            goal="""Create compelling, personalized proposals that clearly
            articulate the value of custom AI solutions for each prospect.
            Your proposals should be professional, specific to their situation,
            and drive action.""",
            backstory="""You are a senior solutions architect and technical writer
            who has crafted winning proposals for Fortune 500 companies. You
            understand how to translate technical capabilities into business value.

            Your proposal philosophy:
            - Lead with their specific pain points, not your capabilities
            - Clearly articulate the proposed solution in business terms
            - Provide realistic timelines and expectations
            - Include clear investment guidance without hard quotes
            - End with compelling next steps

            You write in a confident, consultative tone that positions Nodari AI
            as a trusted partner, not just a vendor. Your proposals are:
            - Concise yet comprehensive
            - Specific to their situation
            - Professionally formatted
            - Action-oriented

            You know that proposals are often shared internally, so you write
            for multiple stakeholders - technical and business.""",
            tools=[create_pdf],
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
        """
        Create a proposal generation task.

        Args:
            agent: The Proposal Agent
            inquiry: Full inquiry record with all context
            analysis: Call analysis results

        Returns:
            Configured Task for proposal generation
        """
        # Build context from inquiry
        research_context = ""
        if inquiry.company_research:
            research = inquiry.company_research
            research_context = f"""
        **Company Research:**
        - Industry: {research.get('industry', 'Unknown')}
        - Size: {research.get('company_size_estimate', 'Unknown')}
        - Summary: {research.get('company_summary', 'Not available')}
        - Pain Points: {', '.join(research.get('pain_points', [])[:3]) or 'Not identified'}
        - AI Opportunities: {', '.join(research.get('ai_opportunities', [])[:3]) or 'Not identified'}
            """

        call_context = ""
        if analysis:
            call_context = f"""
        **Call Insights:**
        - Summary: {analysis.call_summary}
        - Sentiment: {analysis.sentiment.value}
        - Interest Level: {analysis.interest_level}/100
        - Pain Points Discussed: {', '.join(analysis.key_pain_points[:3]) if analysis.key_pain_points else 'None'}
        - Buying Signals: {', '.join(analysis.buying_signals[:3]) if analysis.buying_signals else 'None'}
        - Next Steps Discussed: {', '.join(analysis.next_steps_discussed[:3]) if analysis.next_steps_discussed else 'None'}
            """

        description = f"""
        Create a compelling proposal for {inquiry.company_name}.

        **COMPANY INFORMATION:**
        - Company: {inquiry.company_name}
        - Contact: {inquiry.email}
        - Website: {inquiry.website or 'Not provided'}
        - Primary Goal: {inquiry.primary_goal or 'Not specified'}
        - Business Challenges: {inquiry.business_challenges or 'Not specified'}
        - Data Sources: {inquiry.data_sources or 'Not specified'}
        - Timeline: {inquiry.timeline or 'Not specified'}
        - Infrastructure Criticality: {inquiry.infrastructure_criticality or 'Not specified'}/5

        {research_context}

        {call_context}

        **CREATE A PROPOSAL WITH THESE SECTIONS:**

        1. **EXECUTIVE SUMMARY** (2-3 paragraphs)
           - Hook them with understanding of their situation
           - Briefly introduce the proposed approach
           - Highlight key benefits they'll receive
           - Build confidence in Nodari AI as a partner

           Write this for a busy executive who may only read this section.

        2. **UNDERSTANDING YOUR CHALLENGES** (Problem Statement)
           - Reflect back their stated challenges
           - Show you understand their industry context
           - Connect their challenges to business impact
           - Set up the solution naturally

           Be specific to their situation, not generic.

        3. **PROPOSED SOLUTION** (2-3 paragraphs)
           - Describe the recommended AI approach
           - Explain how it addresses their specific challenges
           - Mention relevant technologies at appropriate level
           - Focus on outcomes, not just features

           Make it understandable to non-technical stakeholders.

        4. **IMPLEMENTATION TIMELINE**
           Provide a realistic timeline with phases:
           - Discovery & Planning (Week 1-2)
           - Development & Training (Weeks 3-8)
           - Testing & Refinement (Weeks 9-10)
           - Deployment & Support (Week 11-12)

           Adjust based on their stated timeline and complexity.

        5. **INVESTMENT**
           Provide range-based guidance:
           - "Projects of this scope typically range from $X to $Y"
           - Explain what drives the range
           - Mention what's included (support, training, etc.)
           - Note that final pricing requires detailed scoping

           Be professional but not salesy.

        6. **NEXT STEPS**
           Clear call-to-action:
           - Confirm the scheduled meeting (if applicable)
           - What to prepare for the meeting
           - What happens after
           - How to reach us with questions

           Make it easy for them to take action.

        7. **WHY NODARI AI** (Brief - 1 paragraph)
           - Relevant expertise
           - Approach to partnerships
           - Commitment to results

        **FORMATTING REQUIREMENTS:**
        - Use proper markdown formatting
        - Include headers with ## for sections
        - Use bullet points for lists
        - Keep paragraphs concise
        - Professional but approachable tone

        **Output Format:**
        Provide a JSON object with:
        - executive_summary: The executive summary section
        - problem_statement: The challenges section
        - proposed_solution: The solution section
        - timeline: The timeline section
        - investment: The investment section
        - next_steps: The next steps section
        - case_studies: List of relevant case study references (can be empty)
        - markdown_content: THE COMPLETE PROPOSAL IN MARKDOWN FORMAT
          (This should be the full, formatted proposal document)
        """

        return Task(
            description=description,
            expected_output="Structured JSON object with proposal content matching ProposalContent schema, including complete markdown_content",
            agent=agent,
            output_pydantic=ProposalContent
        )


def create_proposal_agent() -> Agent:
    """Convenience function to create a Proposal Agent."""
    return ProposalAgentFactory.create()
