"""Retell AI phone call integration tool."""

import logging
from typing import Dict, Any, Optional
import httpx

from src.config import get_settings, format_phone_number
from src.models import PersonalizationContext

logger = logging.getLogger(__name__)


class RetellCaller:
    """
    Retell AI API client for initiating phone calls.

    Handles creating outbound calls with dynamic variables
    that are passed to the Retell AI agent.
    """

    def __init__(self):
        """Initialize Retell client with configuration."""
        settings = get_settings()
        self.api_key = settings.RETELL_API_KEY
        self.agent_id = settings.RETELL_AGENT_ID
        self.from_number = settings.RETELL_FROM_NUMBER
        self.base_url = settings.RETELL_API_URL
        self.webhook_base_url = settings.WEBHOOK_BASE_URL

        logger.info(f"Retell caller initialized - Agent: {self.agent_id}")

    async def create_call(
        self,
        to_number: str,
        dynamic_variables: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create an outbound phone call with dynamic variables.

        Args:
            to_number: Phone number to call (will be formatted)
            dynamic_variables: Variables to pass to Retell agent
            metadata: Additional metadata for the call

        Returns:
            Call ID if successful, None otherwise
        """
        # Format phone number
        formatted_number = format_phone_number(to_number)
        if not formatted_number:
            logger.error(f"Invalid phone number: {to_number}")
            return None

        logger.info(f"Creating Retell call to {formatted_number}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Build request payload
        payload = {
            "from_number": self.from_number,
            "to_number": formatted_number,
            "agent_id": self.agent_id,
            "retell_llm_dynamic_variables": dynamic_variables,
            "metadata": metadata or {}
        }

        # Add webhook URL for call completion events
        if self.webhook_base_url:
            payload["metadata"]["webhook_url"] = f"{self.webhook_base_url}/webhook/retell"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/create-phone-call",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()
                call_id = data.get("call_id")

                if call_id:
                    logger.info(f"Retell call created: {call_id}")
                    return call_id
                else:
                    logger.error(f"No call_id in response: {data}")
                    return None

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Retell API error: {e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"Retell request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Retell call: {e}")
            return None

    def build_dynamic_variables(
        self,
        company_name: str,
        contact_name: Optional[str],
        email: str,
        website: Optional[str],
        primary_goal: Optional[str],
        business_challenges: Optional[str],
        timeline: Optional[str],
        research_summary: Optional[str] = None,
        personalization: Optional[PersonalizationContext] = None
    ) -> Dict[str, str]:
        """
        Build dynamic variables dictionary for Retell agent.

        These variables are injected into the Retell agent's prompt
        during the call.

        Args:
            company_name: Company name
            contact_name: Contact person name (may be same as company)
            email: Contact email
            website: Company website
            primary_goal: Their stated primary goal
            business_challenges: Their stated challenges
            timeline: Their timeline
            research_summary: Summary from Research Agent
            personalization: Output from Personalization Agent

        Returns:
            Dictionary of dynamic variables for Retell
        """
        # Use company name as contact name fallback
        effective_contact = contact_name or company_name

        variables = {
            # Basic info
            "customer_name": effective_contact,
            "company_name": company_name,
            "email": email,
            "website": website or "",

            # Form responses
            "primary_goal": primary_goal or "",
            "business_challenges": business_challenges or "",
            "timeline": timeline or "",

            # Research context (truncated to avoid token limits)
            "research_summary": (research_summary or "")[:1000],
        }

        # Add personalization if available
        if personalization:
            variables.update({
                "opening_hook": personalization.custom_opener,
                "pain_point_reference": personalization.pain_point_reference,
                "value_proposition": personalization.value_proposition,
                "call_strategy": personalization.call_strategy,

                # Objection handlers
                "objection_budget": personalization.objection_handlers.get(
                    "Budget is tight",
                    personalization.objection_handlers.get("budget", "")
                ),
                "objection_timing": personalization.objection_handlers.get(
                    "We're not ready yet",
                    personalization.objection_handlers.get("timing", "")
                ),
                "objection_competition": personalization.objection_handlers.get(
                    "We're exploring other options",
                    personalization.objection_handlers.get("competition", "")
                ),
            })

            # Add talking points as concatenated string
            if personalization.talking_points:
                variables["talking_points"] = " | ".join(personalization.talking_points[:5])

        return variables

    def build_minimal_variables(
        self,
        company_name: str,
        email: str,
        primary_goal: Optional[str] = None,
        business_challenges: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build minimal dynamic variables when research/personalization fails.

        Graceful degradation - still provides basic context to Retell agent.

        Args:
            company_name: Company name
            email: Contact email
            primary_goal: Their stated goal
            business_challenges: Their stated challenges

        Returns:
            Minimal dynamic variables dictionary
        """
        return {
            "customer_name": company_name,
            "company_name": company_name,
            "email": email,
            "primary_goal": primary_goal or "exploring AI solutions",
            "business_challenges": business_challenges or "",
            "research_summary": "",
            "opening_hook": f"Thank you for your interest in Nodari AI, {company_name}.",
            "value_proposition": "We help companies implement custom AI solutions that drive real business results.",
            "call_strategy": "Focus on understanding their needs and building rapport.",
        }

    async def get_call_status(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a call.

        Args:
            call_id: Retell call ID

        Returns:
            Call status data if found
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/get-call/{call_id}",
                    headers=headers,
                    timeout=15.0
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Failed to get call status for {call_id}: {e}")
            return None


# ===========================================
# Singleton Instance
# ===========================================

retell_caller = RetellCaller()
