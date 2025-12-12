"""Retell AI integration for outbound calling."""

import logging
import asyncio
from typing import Optional, Dict, Any
import httpx

from src.core.config import get_settings, format_phone_number

logger = logging.getLogger(__name__)


class RetellService:
    """
    Service for Retell AI API operations.

    Handles creating outbound calls with dynamic variables
    for personalized AI conversations.
    """

    def __init__(self):
        """Initialize service with settings."""
        self._settings = None

    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def create_call(
        self,
        to_number: str,
        dynamic_variables: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create an outbound call via Retell API.

        Args:
            to_number: Phone number to call (will be formatted to E.164)
            dynamic_variables: Variables passed to the AI agent
            metadata: Additional metadata for the call

        Returns:
            Call ID if successful, None otherwise
        """
        formatted_number = format_phone_number(to_number)
        if not formatted_number:
            logger.error(f"Invalid phone number: {to_number}")
            return None

        payload = {
            "agent_id": self.settings.RETELL_AGENT_ID,
            "from_number": self.settings.RETELL_FROM_NUMBER,
            "to_number": formatted_number,
            "retell_llm_dynamic_variables": dynamic_variables,
        }

        if metadata:
            payload["metadata"] = metadata

        headers = {
            "Authorization": f"Bearer {self.settings.RETELL_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.settings.RETELL_API_URL}/create-phone-call",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 201:
                    data = response.json()
                    call_id = data.get("call_id")
                    logger.info(f"Retell call created: {call_id}")
                    return call_id
                else:
                    logger.error(
                        f"Retell API error: {response.status_code} - {response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("Retell API timeout")
            return None
        except Exception as e:
            logger.error(f"Retell API error: {e}")
            return None

    def build_dynamic_variables(
        self,
        company_name: str,
        contact_name: str,
        email: str,
        website: Optional[str] = None,
        primary_goal: Optional[str] = None,
        business_challenges: Optional[str] = None,
        timeline: Optional[str] = None,
        research_summary: Optional[str] = None,
        personalization: Optional["PersonalizationContext"] = None
    ) -> Dict[str, str]:
        """
        Build dynamic variables for Retell agent.

        Args:
            company_name: Company name
            contact_name: Contact person name
            email: Contact email
            website: Company website
            primary_goal: Their stated goal
            business_challenges: Challenges they mentioned
            timeline: Their timeline
            research_summary: AI-generated research
            personalization: Full personalization context

        Returns:
            Dictionary of dynamic variables
        """
        variables = {
            "company_name": company_name or "there",
            "customer_name": contact_name or company_name or "there",
            "email": email or "",
            "website": website or "not provided",
            "primary_goal": primary_goal or "exploring AI solutions",
            "business_challenges": business_challenges or "improving operations",
            "timeline": timeline or "to be determined",
        }

        if research_summary:
            variables["research_summary"] = research_summary[:500]

        if personalization:
            variables["opening_hook"] = personalization.custom_opener[:200]
            variables["pain_point_reference"] = personalization.pain_point_reference[:200]
            variables["value_proposition"] = personalization.value_proposition[:300]
            variables["call_strategy"] = personalization.call_strategy[:300]

            # Add objection handlers
            for obj_type, response in list(personalization.objection_handlers.items())[:3]:
                key = f"objection_{obj_type.lower().replace(' ', '_')[:20]}"
                variables[key] = response[:200]

        return variables

    def build_minimal_variables(
        self,
        company_name: str,
        email: str,
        primary_goal: Optional[str] = None,
        business_challenges: Optional[str] = None
    ) -> Dict[str, str]:
        """Build minimal variables when full personalization unavailable."""
        return {
            "company_name": company_name or "there",
            "customer_name": company_name or "there",
            "email": email or "",
            "primary_goal": primary_goal or "exploring AI solutions",
            "business_challenges": business_challenges or "improving operations",
            "opening_hook": f"Thanks for your interest in Nodari AI, {company_name}!",
            "value_proposition": "We help companies implement custom AI solutions that drive real business results.",
        }


# Forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models import PersonalizationContext

# Singleton instance
retell_service = RetellService()
