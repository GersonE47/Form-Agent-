"""Research Agent for company intelligence gathering."""

import logging
from crewai import Agent, Task
from crewai.tools import tool

from src.models import ParsedLead, CompanyResearch
from src.integrations.firecrawl import firecrawl_service

logger = logging.getLogger(__name__)


class ResearchAgentFactory:
    """Factory for creating Research Agent."""

    @staticmethod
    def create() -> Agent:
        """Create a Research Agent with web scraping tools."""

        @tool("scrape_website")
        def scrape_website(url: str) -> str:
            """
            Scrape a website to extract content.
            Use this to gather information about the company.

            Args:
                url: The website URL to scrape

            Returns:
                Extracted content from the website
            """
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(firecrawl_service.scrape_website(url))

            if result and result.get("success"):
                return result.get("markdown", "No content extracted")
            return f"Failed to scrape website: {result.get('error', 'Unknown error')}"

        @tool("search_news")
        def search_news(query: str) -> str:
            """
            Search for recent news about a company.

            Args:
                query: Search query (e.g., "Company Name news")

            Returns:
                Recent news and articles
            """
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            results = loop.run_until_complete(
                firecrawl_service.search_and_scrape(query, limit=3)
            )

            if results:
                formatted = []
                for r in results:
                    formatted.append(f"- {r['title']}: {r.get('description', '')[:200]}")
                return "\n".join(formatted)
            return "No recent news found"

        return Agent(
            role="Company Research Specialist",
            goal="""Gather comprehensive intelligence about companies to help
            personalize sales conversations and identify AI opportunities.""",
            backstory="""You are an expert business researcher with deep experience
            in B2B sales intelligence. You know how to quickly assess a company's
            profile, identify their pain points, and spot opportunities for AI solutions.

            Your research approach:
            - Start with the company website for official information
            - Look for recent news and announcements
            - Identify industry context and competitive landscape
            - Find specific challenges that AI could address
            - Assess company size and technical sophistication

            You provide actionable insights, not just raw data.""",
            tools=[scrape_website, search_news],
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    @staticmethod
    def create_research_task(agent: Agent, lead: ParsedLead) -> Task:
        """Create a research task for the agent."""
        description = f"""
        Research the company: {lead.company_name}

        **Available Information:**
        - Website: {lead.website or 'Not provided'}
        - Primary Goal: {lead.primary_goal or 'Not specified'}
        - Business Challenges: {lead.business_challenges or 'Not specified'}
        - Email Domain: {lead.email.split('@')[-1] if lead.email else 'Unknown'}

        **Research Tasks:**
        1. If website is provided, scrape it to understand:
           - What the company does
           - Their industry and market
           - Products/services offered
           - Company size indicators

        2. Search for recent news about the company

        3. Based on your findings, identify:
           - Key pain points they likely face
           - Opportunities where AI could help
           - Relevant talking points for sales

        **Output Requirements:**
        Provide structured research with:
        - company_summary: 2-3 sentence overview
        - industry: Primary industry
        - company_size_estimate: Small/Medium/Large or employee estimate
        - tech_stack: Technologies mentioned (if any)
        - recent_news: Notable recent developments
        - pain_points: Business challenges identified
        - ai_opportunities: Where AI could help
        - research_confidence: 0.0-1.0 based on data quality
        """

        return Task(
            description=description,
            expected_output="Structured JSON matching CompanyResearch schema",
            agent=agent,
            output_pydantic=CompanyResearch
        )
