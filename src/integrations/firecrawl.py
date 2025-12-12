"""Firecrawl integration for web scraping."""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from functools import partial

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class FirecrawlService:
    """
    Service for Firecrawl web scraping operations.

    Provides website scraping and search capabilities
    for the Research Agent.
    """

    def __init__(self):
        """Initialize service."""
        self._client = None
        self._settings = None

    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def client(self):
        """Lazy initialize Firecrawl client."""
        if self._client is None:
            try:
                from firecrawl import FirecrawlApp
                self._client = FirecrawlApp(api_key=self.settings.FIRECRAWL_API_KEY)
                logger.info("Firecrawl client initialized")
            except ImportError:
                logger.error("firecrawl-py not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Firecrawl: {e}")
                raise
        return self._client

    async def scrape_website(
        self,
        url: str,
        formats: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape a website and return content.

        Args:
            url: URL to scrape
            formats: Output formats (default: ["markdown"])

        Returns:
            Scraped content including markdown and metadata
        """
        if not url:
            return None

        formats = formats or ["markdown"]

        try:
            # Run sync client in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                partial(self.client.scrape_url, url, params={"formats": formats})
            )

            if result:
                logger.info(f"Scraped {url}: {len(result.get('markdown', ''))} chars")
                return {
                    "url": url,
                    "markdown": result.get("markdown", ""),
                    "html": result.get("html", ""),
                    "metadata": result.get("metadata", {}),
                    "success": True
                }
            return None

        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "success": False
            }

    async def search_and_scrape(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the web and scrape top results.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of scraped results
        """
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                partial(self.client.search, query, params={"limit": limit})
            )

            if results:
                logger.info(f"Search '{query}': {len(results)} results")
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("description", ""),
                        "content": r.get("markdown", r.get("content", ""))
                    }
                    for r in results
                ]
            return []

        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []

    def is_available(self) -> bool:
        """Check if Firecrawl service is configured."""
        return bool(self.settings.FIRECRAWL_API_KEY)


# Singleton instance
firecrawl_service = FirecrawlService()
