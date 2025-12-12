"""Result models for crew outputs and database records."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.enums import LeadStatus
from src.models.lead import CompanyResearch, LeadScoring, PersonalizationContext
from src.models.call import CallAnalysis
from src.models.proposal import ProposalContent


class PreCallResult(BaseModel):
    """Aggregated result from the pre-call crew."""
    success: bool = Field(True, description="Whether the crew completed successfully")
    research: Optional[CompanyResearch] = Field(
        None,
        description="Research agent output"
    )
    scoring: Optional[LeadScoring] = Field(
        None,
        description="Scoring agent output"
    )
    personalization: Optional[PersonalizationContext] = Field(
        None,
        description="Personalization agent output"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Any errors encountered"
    )


class PostCallResult(BaseModel):
    """Aggregated result from the post-call crew."""
    success: bool = Field(True, description="Whether the crew completed successfully")
    analysis: Optional[CallAnalysis] = Field(
        None,
        description="Analysis agent output"
    )
    proposal: Optional[ProposalContent] = Field(
        None,
        description="Proposal agent output (for hot leads)"
    )
    proposal_pdf_path: Optional[str] = Field(
        None,
        description="Path to generated PDF"
    )
    email_sent: bool = Field(False, description="Whether follow-up email was sent")
    meeting_booked: bool = Field(False, description="Whether meeting was booked")
    meeting_link: Optional[str] = Field(
        None,
        description="Calendar meeting link"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Any errors encountered"
    )


class InquiryRecord(BaseModel):
    """Database record for a lead inquiry."""
    id: Optional[str] = Field(None, description="Database record ID")
    company_name: str = Field(..., description="Company name")
    email: str = Field(..., description="Contact email")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    primary_goal: Optional[str] = Field(None, description="Primary AI goal")
    business_challenges: Optional[str] = Field(None, description="Business challenges")
    data_sources: Optional[str] = Field(None, description="Data sources")
    infrastructure_criticality: Optional[int] = Field(None, description="Infrastructure criticality")
    timeline: Optional[str] = Field(None, description="Timeline")
    preferred_datetime: Optional[str] = Field(None, description="Preferred contact time")

    # Processing status
    status: Optional[LeadStatus] = Field(LeadStatus.NEW, description="Current status")

    # Research & scoring
    company_research: Optional[Dict[str, Any]] = Field(None, description="Research data")
    lead_score: Optional[int] = Field(None, description="Lead score 0-100")
    lead_category: Optional[str] = Field(None, description="Lead category")
    scoring_details: Optional[Dict[str, Any]] = Field(None, description="Scoring breakdown")

    # Call data
    retell_call_id: Optional[str] = Field(None, description="Retell call ID")
    call_transcript: Optional[str] = Field(None, description="Call transcript")
    call_recording_url: Optional[str] = Field(None, description="Recording URL")
    call_duration_seconds: Optional[int] = Field(None, description="Call duration")
    call_analysis: Optional[Dict[str, Any]] = Field(None, description="Call analysis")

    # Follow-up
    proposal_url: Optional[str] = Field(None, description="Proposal PDF URL")
    meeting_booked: bool = Field(False, description="Meeting booked status")
    meeting_datetime: Optional[datetime] = Field(None, description="Meeting time")
    meeting_link: Optional[str] = Field(None, description="Meeting link")
    followup_sent: bool = Field(False, description="Follow-up email sent")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Record creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")

    class Config:
        from_attributes = True
