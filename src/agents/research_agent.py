"""Research Agent for company intelligence gathering."""

import logging
from typing import Optional
from crewai import Agent, Task
from crewai_tools import tool

from src.tools.web_scraper import FirecrawlScraper
from src.models import CompanyResearch, ParsedLead

logger = logging.getLogger(__name__)


class ResearchAgentFactory:
    """
    Factory for creating the Research Agent.

    The Research Agent is responsible for gathering comprehensive
    intelligence about prospective companies using web scraping.
    """

    @staticmethod
    def create() -> Agent:
        """
        Create a Research Agent with web scraping tools.

        Returns:
            Configured CrewAI Agent for company research
        """
        # Initialize scraper
        scraper = FirecrawlScraper()

        @tool("scrape_company_website")
        def scrape_website(url: str) -> str:
            """
            Scrape and extract information from a company website.

            Use this tool to gather detailed information about the prospect's
            company from their website. Returns markdown content with
            company description, products/services, and other relevant info.

            Args:
                url: The website URL to scrape (e.g., https://company.com)

            Returns:
                Markdown content with company information
            """
            return scraper.scrape_website(url)

        @tool("search_company_news")
        def search_news(company_name: str) -> str:
            """
            Search for recent news and updates about a company.

            Use this tool to find recent press releases, funding announcements,
            product launches, or other newsworthy events related to the company.

            Args:
                company_name: The name of the company to search for

            Returns:
                Markdown content with relevant news articles
            """
            query = f"{company_name} news recent updates announcements"
            return scraper.search_and_scrape(query, limit=5)

        return Agent(
            role="Senior Business Intelligence Researcher",
            goal="""Conduct comprehensive research on prospective companies to uncover
            business context, pain points, technology stack, and opportunities for
            AI solutions. Your research directly informs sales conversations and
            must be accurate, factual, and actionable.""",
            backstory="""You are a seasoned business analyst with 15 years of experience
            in B2B technology sales intelligence. You have a keen eye for identifying
            business challenges that AI can solve and understand the nuances of different
            industries.

            You specialize in:
            - Extracting key business information from company websites
            - Identifying technology adoption patterns and tech stack
            - Understanding organizational pain points from public information
            - Mapping competitive landscapes
            - Finding recent news and developments

            Your research is thorough yet concise. You focus on information that will
            help sales conversations be more relevant and impactful. You never make
            assumptions - you only report what you can verify from sources.""",
            tools=[scrape_website, search_news],
            verbose=True,
            allow_delegation=False,
            max_iter=5,
            memory=True
        )

    @staticmethod
    def create_research_task(
        agent: Agent,
        lead: ParsedLead
    ) -> Task:
        """
        Create a research task for a specific lead.

        Args:
            agent: The Research Agent
            lead: Parsed lead data with company info

        Returns:
            Configured Task for research
        """
        description = f"""
        Analyze the company {lead.company_name} and gather comprehensive intelligence.

        **Company Website:** {lead.website or 'Not provided - search for their website'}
        **Contact Email Domain:** {lead.email.split('@')[1] if '@' in lead.email else 'Unknown'}

        **Context from their inquiry:**
        - Primary Goal: {lead.primary_goal or 'Not specified'}
        - Business Challenges: {lead.business_challenges or 'Not specified'}
        - Data Sources: {lead.data_sources or 'Not specified'}
        - Timeline: {lead.timeline or 'Not specified'}

        **Your research must include:**

        1. **COMPANY OVERVIEW** (Required)
           - What does the company do?
           - What industry/sector are they in?
           - What products or services do they offer?
           - Who is their target market?

        2. **COMPANY SIZE SIGNALS** (If available)
           - Estimated employee count (look for team pages, LinkedIn, job postings)
           - Number of locations
           - Funding status if a startup

        3. **TECHNOLOGY LANDSCAPE**
           - What technologies, tools, or platforms do they use?
           - Any integrations or partnerships mentioned?
           - Level of technical sophistication

        4. **PAIN POINTS & OPPORTUNITIES**
           - Based on their industry, what challenges might they face?
           - Where could custom AI solutions add value?
           - How do their stated challenges align with AI opportunities?

        5. **RECENT NEWS** (If available)
           - Any significant announcements?
           - New products, funding, or leadership changes?
           - Industry trends affecting them?

        6. **COMPETITIVE CONTEXT**
           - Who are their main competitors?
           - How do they differentiate?

        **Output Format:**
        Provide your findings as a structured JSON object matching this schema:
        - company_summary: Brief overview (2-3 sentences)
        - industry: Primary industry/sector
        - company_size_estimate: Employee count estimate or "Unknown"
        - tech_stack: List of technologies mentioned
        - recent_news: List of recent news items
        - pain_points: List of identified challenges
        - ai_opportunities: List of AI use cases
        - competitors: List of competitors
        - research_confidence: 0-1 score of how confident you are in findings
        """

        return Task(
            description=description,
            expected_output="Structured JSON object with company research findings matching CompanyResearch schema",
            agent=agent,
            output_pydantic=CompanyResearch
        )


def create_research_agent() -> Agent:
    """Convenience function to create a Research Agent."""
    return ResearchAgentFactory.create()
