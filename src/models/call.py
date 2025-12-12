"""Call-related models - Transcript analysis and webhooks."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.models.enums import CallSentiment


class CallAnalysis(BaseModel):
    """Analysis output from the Analysis Agent."""
    call_summary: str = Field(..., description="Brief summary of the call")
    sentiment: CallSentiment = Field(..., description="Overall call sentiment")
    interest_level: int = Field(
        ...,
        ge=0,
        le=100,
        description="Interest level score (0-100)"
    )
    key_pain_points: List[str] = Field(
        default_factory=list,
        description="Pain points mentioned in call"
    )
    objections_raised: List[str] = Field(
        default_factory=list,
        description="Objections or concerns raised"
    )
    buying_signals: List[str] = Field(
        default_factory=list,
        description="Positive buying indicators"
    )
    next_steps_discussed: List[str] = Field(
        default_factory=list,
        description="Action items mentioned"
    )
    meeting_agreed: bool = Field(
        False,
        description="Whether a follow-up meeting was agreed"
    )
    proposed_meeting_time: Optional[str] = Field(
        None,
        description="Suggested meeting time if discussed"
    )
    budget_confirmed: Optional[bool] = Field(
        None,
        description="Whether budget was confirmed"
    )
    timeline_confirmed: Optional[bool] = Field(
        None,
        description="Whether timeline was confirmed"
    )
    decision_maker_confirmed: Optional[bool] = Field(
        None,
        description="Whether speaking to decision maker"
    )
    recommended_action: str = Field(
        ...,
        description="Recommended next action"
    )
    updated_lead_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Updated lead score based on call"
    )


class RetellWebhookPayload(BaseModel):
    """Incoming webhook payload from Retell."""
    event: str = Field(..., description="Event type (e.g., 'call_analyzed')")
    call: Dict[str, Any] = Field(
        default_factory=dict,
        description="Call data including transcript, recording, etc."
    )

    def get_call_id(self) -> Optional[str]:
        """Extract call ID from payload."""
        return self.call.get("call_id")

    def get_transcript(self) -> str:
        """Extract transcript from payload."""
        return self.call.get("transcript", "")

    def get_recording_url(self) -> Optional[str]:
        """Extract recording URL from payload."""
        return self.call.get("recording_url")

    def get_duration(self) -> Optional[int]:
        """Extract call duration in seconds."""
        return self.call.get("call_length_sec") or self.call.get("duration_seconds")

    def get_call_summary(self) -> Optional[str]:
        """Extract call summary if available."""
        analysis = self.call.get("call_analysis", {})
        return analysis.get("call_summary")
