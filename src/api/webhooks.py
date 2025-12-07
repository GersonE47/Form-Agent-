"""Webhook API Routes - Entry points for form and Retell webhooks."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from src.models import RetellWebhookPayload
from src.services.lead_processor import lead_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])


class FormWebhookResponse(BaseModel):
    """Response for form webhook."""
    status: str
    inquiry_id: str
    message: str


class RetellWebhookResponse(BaseModel):
    """Response for Retell webhook."""
    status: str
    message: str


class TestResponse(BaseModel):
    """Response for test endpoints."""
    status: str
    message: str
    data: Dict[str, Any] = {}


# ===========================================
# Form Webhook - Flow 1 Entry Point
# ===========================================

@router.post(
    "/form",
    response_model=FormWebhookResponse,
    status_code=202,
    summary="Process Google Form Submission",
    description="""
    Entry point for Flow 1: Form → Pre-Call Intelligence → Retell Call.

    Receives form data from Google Apps Script, saves to Supabase,
    then runs the pre-call crew in the background before triggering
    a Retell AI call.

    Returns 202 Accepted immediately while processing continues in background.
    """
)
async def form_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> FormWebhookResponse:
    """
    Handle incoming form submission webhook.

    Expected payload from Google Apps Script:
    {
        "Name ": "Company Name",
        "Email": "email@company.com",
        "Phone Number ": "+1234567890",
        "Website ": "https://company.com",
        ...form fields...
    }

    Or wrapped in body:
    {
        "body": { ...form fields... }
    }
    """
    try:
        # Parse raw JSON
        raw_data = await request.json()

        # Handle nested body structure from some Apps Script configs
        if "body" in raw_data and isinstance(raw_data["body"], dict):
            raw_data = raw_data["body"]

        logger.info(f"Received form webhook: {raw_data.get('Email', 'unknown')}")

        # Validate we have minimum required fields
        if not raw_data.get("Email"):
            raise HTTPException(
                status_code=400,
                detail="Missing required field: Email"
            )

        # Process synchronously for now to get inquiry_id
        # (The heavy AI work happens inside process_form_webhook)
        inquiry_id = await lead_processor.process_form_webhook(raw_data)

        return FormWebhookResponse(
            status="accepted",
            inquiry_id=inquiry_id,
            message="Form submission received and processing started"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form webhook error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process form submission: {str(e)}"
        )


# Background task wrapper for form processing
async def _process_form_background(raw_data: Dict[str, Any]):
    """Background task for form processing."""
    try:
        await lead_processor.process_form_webhook(raw_data)
    except Exception as e:
        logger.error(f"Background form processing failed: {e}")


# ===========================================
# Retell Webhook - Flow 2 Entry Point
# ===========================================

@router.post(
    "/retell",
    response_model=RetellWebhookResponse,
    status_code=202,
    summary="Process Retell Call Webhook",
    description="""
    Entry point for Flow 2: Retell Webhook → Post-Call Intelligence.

    Receives webhook from Retell after call completion. Only processes
    'call_analyzed' events. Runs post-call analysis and follow-up
    actions in the background.

    Returns 202 Accepted immediately while processing continues in background.
    """
)
async def retell_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> RetellWebhookResponse:
    """
    Handle incoming Retell webhook.

    Expected payload:
    {
        "event": "call_analyzed",
        "call": {
            "call_id": "...",
            "transcript": "...",
            "recording_url": "...",
            "call_length_sec": 120,
            "call_analysis": { "call_summary": "..." }
        }
    }

    Or wrapped in body:
    {
        "body": { "event": "...", "call": {...} }
    }
    """
    try:
        # Parse raw JSON
        raw_data = await request.json()

        # Handle nested body structure
        if "body" in raw_data and isinstance(raw_data["body"], dict):
            raw_data = raw_data["body"]

        # Parse into Retell payload model
        payload = RetellWebhookPayload(**raw_data)

        logger.info(f"Received Retell webhook: event={payload.event}")

        # Only process call_analyzed events
        if payload.event != "call_analyzed":
            return RetellWebhookResponse(
                status="ignored",
                message=f"Event '{payload.event}' ignored - only 'call_analyzed' is processed"
            )

        # Process in background
        background_tasks.add_task(_process_retell_background, payload)

        return RetellWebhookResponse(
            status="accepted",
            message="Retell webhook received and processing started"
        )

    except Exception as e:
        logger.error(f"Retell webhook error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process Retell webhook: {str(e)}"
        )


async def _process_retell_background(payload: RetellWebhookPayload):
    """Background task for Retell webhook processing."""
    try:
        await lead_processor.process_retell_webhook(payload)
    except Exception as e:
        logger.error(f"Background Retell processing failed: {e}")


# ===========================================
# Status & Test Endpoints
# ===========================================

@router.get(
    "/status/{inquiry_id}",
    summary="Get Inquiry Status",
    description="Retrieve the current status and details of an inquiry."
)
async def get_inquiry_status(inquiry_id: str) -> Dict[str, Any]:
    """Get the current status of an inquiry."""
    try:
        inquiry = await lead_processor.get_inquiry_status(inquiry_id)

        if not inquiry:
            raise HTTPException(
                status_code=404,
                detail=f"Inquiry not found: {inquiry_id}"
            )

        return {
            "inquiry_id": inquiry.id,
            "company_name": inquiry.company_name,
            "email": inquiry.email,
            "status": inquiry.status.value if inquiry.status else "unknown",
            "lead_score": inquiry.lead_score,
            "lead_category": inquiry.lead_category,
            "retell_call_id": inquiry.retell_call_id,
            "meeting_booked": inquiry.meeting_booked,
            "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get inquiry status: {str(e)}"
        )


# ===========================================
# Test Endpoints (Development Only)
# ===========================================

test_router = APIRouter(prefix="/test", tags=["testing"])


@test_router.post(
    "/pre-call",
    response_model=TestResponse,
    summary="Test Pre-Call Pipeline",
    description="Test the pre-call intelligence pipeline without triggering Retell call."
)
async def test_pre_call(request: Request) -> TestResponse:
    """
    Test pre-call pipeline without making actual Retell call.

    Useful for testing research, scoring, and personalization agents.
    """
    try:
        raw_data = await request.json()

        # Handle nested body
        if "body" in raw_data and isinstance(raw_data["body"], dict):
            raw_data = raw_data["body"]

        # Parse lead
        lead = lead_processor.parse_form_submission(raw_data)

        # Run pre-call crew
        from src.crews.pre_call_crew import PreCallCrew
        crew = PreCallCrew()
        result = crew.run(lead)

        return TestResponse(
            status="success" if result.success else "partial",
            message="Pre-call pipeline completed",
            data={
                "company_name": lead.company_name,
                "research": result.research.model_dump() if result.research else None,
                "scoring": result.scoring.model_dump() if result.scoring else None,
                "personalization": result.personalization.model_dump() if result.personalization else None,
                "errors": result.errors
            }
        )

    except Exception as e:
        logger.error(f"Test pre-call error: {e}")
        return TestResponse(
            status="error",
            message=str(e),
            data={}
        )


@test_router.post(
    "/post-call",
    response_model=TestResponse,
    summary="Test Post-Call Pipeline",
    description="Test the post-call analysis pipeline with a sample transcript."
)
async def test_post_call(request: Request) -> TestResponse:
    """
    Test post-call pipeline with sample data.

    Expected payload:
    {
        "transcript": "...",
        "call_summary": "...",
        "company_name": "Test Company",
        "email": "test@test.com"
    }
    """
    try:
        data = await request.json()

        # Create mock inquiry
        from src.models import InquiryRecord, LeadStatus
        from datetime import datetime

        inquiry = InquiryRecord(
            id="test-inquiry-id",
            company_name=data.get("company_name", "Test Company"),
            email=data.get("email", "test@test.com"),
            status=LeadStatus.CALL_COMPLETED,
            created_at=datetime.now()
        )

        # Run post-call crew
        from src.crews.post_call_crew import PostCallCrew
        crew = PostCallCrew()
        result = crew.run(
            inquiry=inquiry,
            transcript=data.get("transcript", "Sample transcript"),
            call_summary=data.get("call_summary")
        )

        return TestResponse(
            status="success" if result.success else "partial",
            message="Post-call pipeline completed",
            data={
                "analysis": result.analysis.model_dump() if result.analysis else None,
                "proposal_generated": result.proposal is not None,
                "email_sent": result.email_sent,
                "meeting_booked": result.meeting_booked,
                "errors": result.errors
            }
        )

    except Exception as e:
        logger.error(f"Test post-call error: {e}")
        return TestResponse(
            status="error",
            message=str(e),
            data={}
        )


@test_router.get(
    "/health",
    summary="Health Check",
    description="Simple health check endpoint."
)
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "nodari-sales-engine"
    }
