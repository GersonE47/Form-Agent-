"""Firecrawl web scraper tool for company research."""

import logging
from typing import Optional, Dict, Any, List
from firecrawl import FirecrawlApp

from src.config import get_settings

logger = logging.getLogger(__name__)


class FirecrawlScraper:
    """
    Firecrawl-based web scraper for company research.

    Uses Firecrawl API to scrape websites and extract structured data
    for the Research Agent.
    """

    def __init__(self):
        """Initialize Firecrawl client."""
        settings = get_settings()
        self.app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
        logger.info("Firecrawl scraper initialized")

    def scrape_website(self, url: str) -> str:
        """
        Scrape a website and return markdown content.

        Args:
            url: Website URL to scrape

        Returns:
            Markdown content of the page
        """
        try:
            logger.info(f"Scraping website: {url}")

            result = self.app.scrape_url(
                url,
                params={
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                    "timeout": 30000,
                    "waitFor": 2000,  # Wait for dynamic content
                }
            )

            markdown_content = result.get("markdown", "")

            if markdown_content:
                logger.info(f"Successfully scraped {url}: {len(markdown_content)} chars")
                return markdown_content
            else:
                logger.warning(f"No content extracted from {url}")
                return f"Unable to extract content from {url}"

        except Exception as e:
            logger.error(f"Firecrawl scrape failed for {url}: {e}")
            return f"Scraping failed: {str(e)}"

    def scrape_with_extraction(
        self,
        url: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Scrape website with structured data extraction.

        Args:
            url: Website URL to scrape
            schema: JSON schema for extraction

        Returns:
            Extracted structured data
        """
        try:
            logger.info(f"Scraping with extraction: {url}")

            result = self.app.scrape_url(
                url,
                params={
                    "formats": [
                        {"type": "json", "schema": schema}
                    ],
                    "onlyMainContent": True,
                    "timeout": 30000,
                }
            )

            extracted = result.get("json", {})

            if extracted:
                logger.info(f"Extracted structured data from {url}")
                return extracted
            else:
                logger.warning(f"No structured data extracted from {url}")
                return {}

        except Exception as e:
            logger.error(f"Structured extraction failed for {url}: {e}")
            return {}

    def search_and_scrape(
        self,
        query: str,
        limit: int = 5
    ) -> str:
        """
        Search for pages and scrape results.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            Combined markdown content from search results
        """
        try:
            logger.info(f"Search and scrape: {query}")

            results = self.app.search(
                query,
                params={
                    "limit": limit,
                    "scrapeOptions": {
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                    }
                }
            )

            combined_content = []
            for result in results.get("data", []):
                url = result.get("url", "Unknown source")
                content = result.get("markdown", "")[:2000]  # Limit per result
                if content:
                    combined_content.append(f"## Source: {url}\n\n{content}")

            if combined_content:
                final_content = "\n\n---\n\n".join(combined_content)
                logger.info(f"Search returned {len(combined_content)} results")
                return final_content
            else:
                logger.warning(f"No results for search: {query}")
                return f"No results found for: {query}"

        except Exception as e:
            logger.error(f"Search and scrape failed for '{query}': {e}")
            return f"Search failed: {str(e)}"

    def crawl_website(
        self,
        url: str,
        max_pages: int = 10,
        include_paths: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Crawl multiple pages of a website.

        Args:
            url: Starting URL
            max_pages: Maximum pages to crawl
            include_paths: URL patterns to include

        Returns:
            List of {url, content} dictionaries
        """
        try:
            logger.info(f"Crawling website: {url} (max {max_pages} pages)")

            crawl_params = {
                "limit": max_pages,
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                }
            }

            if include_paths:
                crawl_params["includePaths"] = include_paths

            # Start crawl (async operation)
            crawl_result = self.app.crawl_url(url, params=crawl_params, wait_until_done=True)

            pages = []
            for page in crawl_result.get("data", []):
                pages.append({
                    "url": page.get("url", ""),
                    "content": page.get("markdown", "")[:5000]  # Limit per page
                })

            logger.info(f"Crawled {len(pages)} pages from {url}")
            return pages

        except Exception as e:
            logger.error(f"Crawl failed for {url}: {e}")
            return []

    def get_company_info(self, website_url: str) -> Dict[str, Any]:
        """
        Get comprehensive company information from their website.

        This is a convenience method that combines scraping with
        common company data extraction.

        Args:
            website_url: Company website URL

        Returns:
            Dictionary with company information
        """
        # Company extraction schema
        schema = {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "description": {"type": "string"},
                "industry": {"type": "string"},
                "products_services": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "target_market": {"type": "string"},
                "founding_info": {"type": "string"},
                "team_size_hints": {"type": "string"},
                "contact_info": {"type": "string"},
                "recent_news": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }

        # Try structured extraction first
        extracted = self.scrape_with_extraction(website_url, schema)

        if extracted:
            return extracted

        # Fallback to plain markdown scraping
        markdown = self.scrape_website(website_url)
        return {
            "raw_content": markdown,
            "extraction_failed": True
        }


# ===========================================
# CrewAI Tool Functions
# ===========================================

def create_scrape_website_tool():
    """Create a CrewAI-compatible tool for website scraping."""
    scraper = FirecrawlScraper()

    def scrape_website(url: str) -> str:
        """
        Scrape and extract information from a company website.

        Args:
            url: The website URL to scrape

        Returns:
            Markdown content with company information
        """
        return scraper.scrape_website(url)

    return scrape_website


def create_search_news_tool():
    """Create a CrewAI-compatible tool for news search."""
    scraper = FirecrawlScraper()

    def search_company_news(company_name: str) -> str:
        """
        Search for recent news and updates about a company.

        Args:
            company_name: Name of the company to search for

        Returns:
            Relevant news articles and press releases
        """
        query = f"{company_name} news recent updates announcements"
        return scraper.search_and_scrape(query, limit=5)

    return search_company_news
