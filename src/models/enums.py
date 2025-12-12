"""Enumeration types for the sales engine."""

from enum import Enum


class LeadStatus(str, Enum):
    """Status progression for leads through the pipeline."""
    NEW = "new"
    RESEARCHING = "researching"
    RESEARCH_COMPLETE = "research_complete"
    RESEARCH_FAILED = "research_failed"
    CALL_SCHEDULED = "call_scheduled"
    CALL_IN_PROGRESS = "call_in_progress"
    CALL_COMPLETED = "call_completed"
    CALL_FAILED = "call_failed"
    ANALYZING = "analyzing"
    HOT_LEAD = "hot_lead"
    WARM_LEAD = "warm_lead"
    NURTURE = "nurture"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class LeadCategory(str, Enum):
    """Lead qualification categories based on scoring."""
    HOT = "hot"
    WARM = "warm"
    NURTURE = "nurture"


class CallSentiment(str, Enum):
    """Sentiment analysis result for calls."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
