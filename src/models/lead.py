"""Lead-related models - Pre-call data structures."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class ParsedLead(BaseModel):
    """Normalized lead data from form submission."""
    company_name: str = Field(..., description="Company or contact name")
    email: EmailStr = Field(..., description="Contact email")
    phone: Optional[str] = Field(None, description="Phone number in E.164 format")
    website: Optional[str] = Field(None, description="Company website URL")
    primary_goal: Optional[str] = Field(None, description="Primary AI implementation goal")
    business_challenges: Optional[str] = Field(None, description="Key business challenges")
    data_sources: Optional[str] = Field(None, description="Relevant data sources")
    infrastructure_criticality: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="How critical is on-premise infrastructure (1-5)"
    )
    timeline: Optional[str] = Field(None, description="Expected timeline for AI solution")
    preferred_datetime: Optional[str] = Field(None, description="Preferred follow-up time")
    form_id: Optional[str] = Field(None, description="Google Form ID")
    submitted_at: Optional[str] = Field(None, description="Form submission timestamp")
    raw_form_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Original form data for reference"
    )


class CompanyResearch(BaseModel):
    """Research output from the Research Agent."""
    company_summary: str = Field(..., description="Brief company overview")
    industry: str = Field(..., description="Primary industry")
    company_size_estimate: Optional[str] = Field(
        None,
        description="Estimated company size (employees/revenue)"
    )
    tech_stack: List[str] = Field(
        default_factory=list,
        description="Known technologies used"
    )
    recent_news: List[str] = Field(
        default_factory=list,
        description="Recent news or announcements"
    )
    pain_points: List[str] = Field(
        default_factory=list,
        description="Identified business pain points"
    )
    ai_opportunities: List[str] = Field(
        default_factory=list,
        description="Potential AI use cases"
    )
    competitors: List[str] = Field(
        default_factory=list,
        description="Known competitors"
    )
    key_contacts: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Key people found (name, title, LinkedIn)"
    )
    research_confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in research accuracy (0-1)"
    )


class LeadScoring(BaseModel):
    """Lead scoring output from the Scoring Agent."""
    total_score: int = Field(..., ge=0, le=100, description="Overall lead score")
    category: "LeadCategory" = Field(..., description="Lead category based on score")
    budget_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Budget/authority indicator score"
    )
    timeline_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Timeline urgency score"
    )
    fit_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Product/service fit score"
    )
    engagement_score: int = Field(
        ...,
        ge=0,
        le=25,
        description="Engagement level score"
    )
    scoring_rationale: str = Field(..., description="Explanation of the scoring")
    priority_notes: Optional[str] = Field(
        None,
        description="Special notes for sales team"
    )


# Import here to avoid circular imports
from src.models.enums import LeadCategory
LeadScoring.model_rebuild()


class PersonalizationContext(BaseModel):
    """Call personalization output from the Personalization Agent."""
    custom_opener: str = Field(
        ...,
        description="Personalized opening line for the call"
    )
    pain_point_reference: str = Field(
        ...,
        description="Specific pain point to reference"
    )
    value_proposition: str = Field(
        ...,
        description="Tailored value proposition"
    )
    talking_points: List[str] = Field(
        default_factory=list,
        description="Key points to cover in the call"
    )
    suggested_questions: List[str] = Field(
        default_factory=list,
        description="Discovery questions to ask"
    )
    objection_handlers: Dict[str, str] = Field(
        default_factory=dict,
        description="Potential objections and responses"
    )
    call_strategy: str = Field(
        ...,
        description="Overall strategy for the call"
    )
