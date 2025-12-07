"""Configuration management for Nodari Sales Engine."""

import os
from functools import lru_cache
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ===========================================
    # Supabase Configuration
    # ===========================================
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_KEY: str = Field(..., description="Supabase anon key")

    # ===========================================
    # OpenAI Configuration (for CrewAI)
    # ===========================================
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview", description="Model for CrewAI agents")

    # ===========================================
    # Retell AI Configuration
    # ===========================================
    RETELL_API_KEY: str = Field(
        default="key_2e5cca188be7ee662cc822b137f0",
        description="Retell AI API key"
    )
    RETELL_AGENT_ID: str = Field(
        default="agent_a045eb2c986224824cdda7c531",
        description="Retell AI agent ID"
    )
    RETELL_FROM_NUMBER: str = Field(
        default="+18883257459",
        description="Outbound phone number"
    )
    RETELL_API_URL: str = Field(
        default="https://api.retellai.com/v2",
        description="Retell API base URL"
    )

    # ===========================================
    # Firecrawl Configuration
    # ===========================================
    FIRECRAWL_API_KEY: str = Field(..., description="Firecrawl API key for web scraping")

    # ===========================================
    # Google Service Account Configuration
    # ===========================================
    GOOGLE_CREDENTIALS_PATH: str = Field(
        default="./credentials/google-service-account.json",
        description="Path to Google service account JSON"
    )
    GOOGLE_CALENDAR_ID: str = Field(
        default="admin@nodari.ai",
        description="Calendar ID to book meetings"
    )

    # ===========================================
    # Server Configuration
    # ===========================================
    WEBHOOK_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL for webhooks"
    )
    DEBUG: bool = Field(default=True, description="Debug mode")

    # ===========================================
    # Lead Scoring Thresholds
    # ===========================================
    HOT_THRESHOLD: int = Field(default=70, description="Score threshold for HOT leads")
    WARM_THRESHOLD: int = Field(default=40, description="Score threshold for WARM leads")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# ===========================================
# Google Form Field Mapping
# ===========================================
# Maps Google Form field names (including trailing spaces) to internal field names
# Update this mapping if your Google Form field names change

GOOGLE_FORM_FIELD_MAPPING: Dict[str, str] = {
    # Basic contact info (note trailing spaces from Google Forms)
    "Name ": "company_name",
    "Name": "company_name",  # Fallback without space
    "Email": "email",
    "Phone Number ": "phone",
    "Phone Number": "phone",  # Fallback
    "Website ": "website",
    "Website": "website",  # Fallback

    # Form questions
    "What is your primary goal for implementing a custom AI system?": "primary_goal",
    "Please briefly describe the key business processes or challenges you are looking to address with AI.": "business_challenges",
    "Which of the following data sources are most relevant to your potential AI system?": "data_sources",
    "On a scale of 1 to 5, how critical is it for the AI system to operate entirely within your existing infrastructure?": "infrastructure_criticality",
    "What is your estimated timeline for launching a custom AI solution?": "timeline",
    "What date and time would you prefer for a follow-up discussion?": "preferred_datetime",

    # Metadata fields
    "formId": "form_id",
    "submittedAt": "submitted_at",
    "timestamp": "submitted_at",
}


def map_form_fields(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Google Form fields to internal field names.

    Handles:
    - Field names with trailing spaces
    - Direct field name matching
    - Passthrough of unmapped fields

    Args:
        raw_data: Raw form submission data from Google Apps Script

    Returns:
        Dictionary with normalized field names
    """
    result = {}

    for raw_key, value in raw_data.items():
        # Try exact match first
        if raw_key in GOOGLE_FORM_FIELD_MAPPING:
            mapped_key = GOOGLE_FORM_FIELD_MAPPING[raw_key]
        # Try stripped key
        elif raw_key.strip() in GOOGLE_FORM_FIELD_MAPPING:
            mapped_key = GOOGLE_FORM_FIELD_MAPPING[raw_key.strip()]
        # Keep original key if no mapping found
        else:
            mapped_key = raw_key.strip().lower().replace(" ", "_")

        # Handle array values (Google Forms returns arrays)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) if value else None

        result[mapped_key] = value

    return result


def format_phone_number(phone: str) -> str:
    """
    Format phone number for Retell API.

    Ensures phone number is in E.164 format: +1XXXXXXXXXX

    Args:
        phone: Raw phone number string

    Returns:
        Formatted phone number with +1 prefix
    """
    if not phone:
        return ""

    # Remove all non-numeric characters
    digits = "".join(c for c in str(phone) if c.isdigit())

    # Handle different formats
    if len(digits) == 10:
        # US number without country code
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        # US number with country code
        return f"+{digits}"
    elif digits.startswith("+"):
        return digits
    else:
        # Assume US and add +1
        return f"+1{digits[-10:]}" if len(digits) >= 10 else f"+1{digits}"


def parse_infrastructure_criticality(value: Any) -> Optional[int]:
    """
    Parse infrastructure criticality score from form.

    Args:
        value: Raw value from form (could be string, int, etc.)

    Returns:
        Integer 1-5 or None
    """
    if value is None:
        return None

    try:
        score = int(str(value).strip())
        return score if 1 <= score <= 5 else None
    except (ValueError, TypeError):
        return None


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance loaded from environment
    """
    return Settings()


# ===========================================
# Retell Dynamic Variable Names
# ===========================================
# These are the variable names expected by the Retell AI agent
# Update your Retell agent prompt to use these variables

RETELL_DYNAMIC_VARS = {
    "customer_name": "Contact/company name",
    "company_name": "Company name",
    "email": "Contact email",
    "website": "Company website",
    "primary_goal": "Their stated primary goal",
    "business_challenges": "Challenges they mentioned",
    "timeline": "Their timeline",
    "research_summary": "AI-generated research summary",
    "opening_hook": "Personalized conversation opener",
    "pain_point_reference": "Reference to their specific pain points",
    "value_proposition": "Tailored value proposition",
    "call_strategy": "Recommended approach for the call",
    "objection_budget": "Response for budget objections",
    "objection_timing": "Response for timing objections",
}


# ===========================================
# Status Constants
# ===========================================
class LeadStatus:
    """Lead status values for tracking progress."""
    NEW = "new"
    RESEARCHED = "researched"
    RESEARCH_FAILED = "research_failed"
    CALL_INITIATED = "call_initiated"
    CALL_FAILED = "call_failed"
    CALL_COMPLETED = "call_completed"
    ANALYZED = "analyzed"
    HOT_PROCESSED = "hot_processed"
    WARM_PROCESSED = "warm_processed"
    NURTURE_PROCESSED = "nurture_processed"
    PROCESSING_FAILED = "processing_failed"


class LeadTier:
    """Lead tier classifications."""
    HOT = "hot"
    WARM = "warm"
    NURTURE = "nurture"
