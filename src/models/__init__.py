"""Models package - All Pydantic models organized by domain."""

from src.models.enums import LeadStatus, LeadCategory, CallSentiment
from src.models.lead import ParsedLead, CompanyResearch, LeadScoring, PersonalizationContext
from src.models.call import CallAnalysis, RetellWebhookPayload
from src.models.proposal import ProposalContent
from src.models.results import PreCallResult, PostCallResult, InquiryRecord

__all__ = [
    # Enums
    "LeadStatus",
    "LeadCategory",
    "CallSentiment",
    # Lead models
    "ParsedLead",
    "CompanyResearch",
    "LeadScoring",
    "PersonalizationContext",
    # Call models
    "CallAnalysis",
    "RetellWebhookPayload",
    # Proposal models
    "ProposalContent",
    # Result models
    "PreCallResult",
    "PostCallResult",
    "InquiryRecord",
]
