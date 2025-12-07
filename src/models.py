"""Pydantic models for Nodari Sales Engine."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, field_validator


# ===========================================
# Enums
# ===========================================

class LeadCategory(str, Enum):
    """Lead classification tiers."""
    HOT = "hot"
    WARM = "warm"
    NURTURE = "nurture"


class CallSentiment(str, Enum):
    """Call sentiment classifications."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


# ===========================================
# Form Submission Models
# ===========================================

class FormSubmission(BaseModel):
    """Raw Google Form submission - flexible to handle any fields."""
    raw_data: Dict[str, Any]

    @field_validator("raw_data", mode="before")
    @classmethod
    def normalize_keys(cls, v: Any) -> Dict[str, Any]:
        """Strip whitespace from keys and handle arrays."""
        if not isinstance(v, dict):
            return v
        result = {}
        for key, value in v.items():
            # Strip key whitespace
            clean_key = key.strip() if isinstance(key, str) else key
            # Handle Google Forms array values
            if isinstance(value, list):
                value = value[0] if len(value) == 1 else ", ".join(str(x) for x in value)
            result[clean_key] = value
        return result


class ParsedLead(BaseModel):
    """Normalized lead data after field mapping."""
    company_name: str
    email: EmailStr
    phone: str
    website: Optional[str] = None
    primary_goal: Optional[str] = None
    business_challenges: Optional[str] = None
    data_sources: Optional[str] = None
    infrastructure_criticality: Optional[int] = Field(None, ge=1, le=5)
    timeline: Optional[str] = None
    preferred_datetime: Optional[str] = None
    form_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    raw_form_data: Optional[Dict[str, Any]] = None

    @field_validator("infrastructure_criticality", mode="before")
    @classmethod
    def parse_criticality(cls, v: Any) -> Optional[int]:
        """Parse infrastructure criticality as integer."""
        if v is None:
            return None
        try:
            return int(str(v).strip())
        except (ValueError, TypeError):
            return None


# ===========================================
# Research Agent Models
# ===========================================

class CompanyResearch(BaseModel):
    """Output from Research Agent - comprehensive company intelligence."""
    company_summary: str = Field(description="Brief overview of what the company does")
    industry: str = Field(description="Primary industry/sector")
    company_size_estimate: Optional[str] = Field(None, description="Estimated employee count")
    tech_stack: List[str] = Field(default_factory=list, description="Technologies/tools they use")
    recent_news: List[str] = Field(default_factory=list, description="Recent news or updates")
    pain_points: List[str] = Field(default_factory=list, description="Identified business challenges")
    ai_opportunities: List[str] = Field(default_factory=list, description="Potential AI use cases")
    competitors: List[str] = Field(default_factory=list, description="Known competitors")
    linkedin_data: Optional[Dict[str, Any]] = Field(None, description="LinkedIn company data")
    research_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in research accuracy")


# ===========================================
# Scoring Agent Models
# ===========================================

class LeadScoring(BaseModel):
    """Output from Scoring Agent - lead qualification results."""
    total_score: int = Field(ge=0, le=100, description="Overall lead score 0-100")
    category: LeadCategory = Field(description="Lead tier classification")

    # Individual component scores (each 0-25)
    budget_score: int = Field(ge=0, le=25, description="Budget/investment signals")
    timeline_score: int = Field(ge=0, le=25, description="Urgency/timeline signals")
    fit_score: int = Field(ge=0, le=25, description="ICP fit score")
    engagement_score: int = Field(ge=0, le=25, description="Form engagement quality")

    scoring_rationale: str = Field(description="Detailed explanation of scoring")
    priority_notes: Optional[str] = Field(None, description="Special notes about this lead")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> LeadCategory:
        """Normalize category to enum."""
        if isinstance(v, LeadCategory):
            return v
        if isinstance(v, str):
            return LeadCategory(v.lower())
        return LeadCategory.WARM


# ===========================================
# Personalization Agent Models
# ===========================================

class PersonalizationContext(BaseModel):
    """Output from Personalization Agent - call strategy and talking points."""
    custom_opener: str = Field(description="Personalized conversation opener")
    pain_point_reference: str = Field(description="How to reference their specific challenges")
    value_proposition: str = Field(description="Tailored value proposition")
    talking_points: List[str] = Field(default_factory=list, description="Key points to cover")
    suggested_questions: List[str] = Field(default_factory=list, description="Discovery questions to ask")
    objection_handlers: Dict[str, str] = Field(
        default_factory=dict,
        description="Prepared responses for common objections"
    )
    call_strategy: str = Field(description="Overall approach recommendation")


# ===========================================
# Analysis Agent Models (Post-Call)
# ===========================================

class CallAnalysis(BaseModel):
    """Output from Analysis Agent - post-call transcript analysis."""
    call_summary: str = Field(description="Brief summary of the call")
    sentiment: CallSentiment = Field(description="Overall prospect sentiment")
    interest_level: int = Field(ge=0, le=100, description="Interest level 0-100")

    key_pain_points: List[str] = Field(default_factory=list, description="Pain points discussed")
    objections_raised: List[str] = Field(default_factory=list, description="Objections or concerns")
    buying_signals: List[str] = Field(default_factory=list, description="Positive buying indicators")
    next_steps_discussed: List[str] = Field(default_factory=list, description="Follow-up actions mentioned")

    meeting_agreed: bool = Field(default=False, description="Did they agree to a meeting?")
    proposed_meeting_time: Optional[str] = Field(None, description="Mentioned meeting time")

    budget_confirmed: Optional[bool] = Field(None, description="Was budget discussed/confirmed?")
    timeline_confirmed: Optional[bool] = Field(None, description="Was timeline confirmed?")
    decision_maker_confirmed: Optional[bool] = Field(None, description="Are they the decision maker?")

    recommended_action: str = Field(description="Recommended next step")
    updated_lead_score: Optional[int] = Field(None, ge=0, le=100, description="Updated score based on call")

    @field_validator("sentiment", mode="before")
    @classmethod
    def normalize_sentiment(cls, v: Any) -> CallSentiment:
        """Normalize sentiment to enum."""
        if isinstance(v, CallSentiment):
            return v
        if isinstance(v, str):
            v_lower = v.lower()
            if "positive" in v_lower:
                return CallSentiment.POSITIVE
            elif "negative" in v_lower:
                return CallSentiment.NEGATIVE
            return CallSentiment.NEUTRAL
        return CallSentiment.NEUTRAL


# ===========================================
# Proposal Agent Models
# ===========================================

class ProposalContent(BaseModel):
    """Output from Proposal Agent - generated proposal content."""
    executive_summary: str = Field(description="Executive summary paragraph")
    problem_statement: str = Field(description="Their challenges we'll address")
    proposed_solution: str = Field(description="Our recommended approach")
    timeline: str = Field(description="Implementation timeline")
    investment: str = Field(description="Investment/pricing information")
    next_steps: str = Field(description="Clear call-to-action")
    case_studies: List[str] = Field(default_factory=list, description="Relevant case studies")
    markdown_content: str = Field(description="Full proposal in markdown format")


# ===========================================
# Crew Result Models
# ===========================================

class PreCallResult(BaseModel):
    """Combined output from Pre-Call Crew."""
    research: Optional[CompanyResearch] = None
    scoring: Optional[LeadScoring] = None
    personalization: Optional[PersonalizationContext] = None
    errors: List[str] = Field(default_factory=list)
    success: bool = True


class PostCallResult(BaseModel):
    """Combined output from Post-Call Crew."""
    analysis: Optional[CallAnalysis] = None
    proposal: Optional[ProposalContent] = None
    proposal_pdf_path: Optional[str] = None
    meeting_booked: bool = False
    meeting_link: Optional[str] = None
    email_sent: bool = False
    errors: List[str] = Field(default_factory=list)
    success: bool = True


# ===========================================
# Webhook Payload Models
# ===========================================

class RetellCallData(BaseModel):
    """Retell call data from webhook."""
    call_id: str
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    call_analysis: Optional[Dict[str, Any]] = None
    retell_llm_dynamic_variables: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class RetellWebhookPayload(BaseModel):
    """Retell webhook payload structure."""
    event: str
    call: Dict[str, Any]

    @property
    def call_data(self) -> RetellCallData:
        """Parse call data from webhook."""
        return RetellCallData(**self.call)


# ===========================================
# Database Record Model
# ===========================================

class InquiryRecord(BaseModel):
    """Full Supabase inquiry record schema."""
    # Primary key
    id: Optional[str] = None
    created_at: Optional[datetime] = None

    # Form data
    company_name: str
    email: str
    phone: str
    website: Optional[str] = None
    primary_goal: Optional[str] = None
    business_challenges: Optional[str] = None
    data_sources: Optional[str] = None
    infrastructure_criticality: Optional[int] = None
    timeline: Optional[str] = None
    preferred_datetime: Optional[str] = None
    form_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    raw_form_data: Optional[Dict[str, Any]] = None

    # Research Agent outputs
    company_research: Optional[Dict[str, Any]] = None

    # Scoring Agent outputs
    lead_score: Optional[int] = None
    lead_category: Optional[str] = None
    scoring_details: Optional[Dict[str, Any]] = None

    # Personalization outputs (stored for reference)
    personalization_data: Optional[Dict[str, Any]] = None

    # Retell call data
    retell_call_id: Optional[str] = None
    call_transcript: Optional[str] = None
    call_recording_url: Optional[str] = None
    call_duration_seconds: Optional[int] = None

    # Analysis Agent outputs (post-call)
    call_analysis: Optional[Dict[str, Any]] = None

    # Proposal Agent outputs
    proposal_url: Optional[str] = None
    proposal_sent_at: Optional[datetime] = None

    # Meeting/Calendar
    meeting_booked: bool = False
    meeting_datetime: Optional[datetime] = None
    calendar_event_id: Optional[str] = None
    meeting_link: Optional[str] = None

    # Follow-up tracking
    followup_sent: bool = False
    followup_type: Optional[str] = None  # hot_proposal, warm_case_study, nurture_email

    # Status tracking
    status: str = "new"
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===========================================
# API Response Models
# ===========================================

class WebhookResponse(BaseModel):
    """Standard webhook response."""
    status: str
    message: str
    inquiry_id: Optional[str] = None
    call_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str


class LeadDetailResponse(BaseModel):
    """Detailed lead information response."""
    inquiry: InquiryRecord
    pre_call_result: Optional[PreCallResult] = None
    post_call_result: Optional[PostCallResult] = None
