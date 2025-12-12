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
    summary="Process Google Form Submission"
)
async def form_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> FormWebhookResponse:
    """
    Handle incoming form submission webhook.

    Returns 202 Accepted immediately while heavy AI processing
    runs in the background.
    """
    try:
        raw_data = await request.json()

        # Handle nested body structure from Apps Script
        if "body" in raw_data and isinstance(raw_data["body"], dict):
            raw_data = raw_data["body"]

        logger.info(f"Received form webhook: {raw_data.get('Email', 'unknown')}")

        if not raw_data.get("Email"):
            raise HTTPException(status_code=400, detail="Missing required field: Email")

        # Parse lead first to validate and get company name
        lead = lead_processor.parse_form_submission(raw_data)

        # Create inquiry synchronously to return ID
        from src.core.database import db_service
        inquiry_id = await db_service.create_inquiry(lead)

        if not inquiry_id:
            raise HTTPException(status_code=500, detail="Failed to create inquiry")

        # Run heavy processing in background
        background_tasks.add_task(
            _process_form_background,
            lead,
            inquiry_id
        )

        return FormWebhookResponse(
            status="accepted",
            inquiry_id=inquiry_id,
            message="Form submission received - processing in background"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process: {str(e)}")


async def _process_form_background(lead, inquiry_id: str):
    """Background task for form processing."""
    try:
        from src.core.database import db_service
        from src.intelligence.crews.pre_call import PreCallCrew
        from src.integrations.retell import retell_service

        logger.info(f"Background processing started for {inquiry_id}")

        # Run pre-call crew
        crew = PreCallCrew()
        result = await crew.run_async(lead)

        # Update database
        if result.research or result.scoring:
            await db_service.update_research(
                inquiry_id,
                research_data=result.research.model_dump() if result.research else None,
                lead_score=result.scoring.total_score if result.scoring else 50,
                lead_category=result.scoring.category.value if result.scoring else "warm",
                scoring_details=result.scoring.model_dump() if result.scoring else None
            )

        # Trigger Retell call if phone available
        if lead.phone:
            if result.personalization and result.research:
                dynamic_vars = retell_service.build_dynamic_variables(
                    company_name=lead.company_name,
                    contact_name=lead.company_name,
                    email=lead.email,
                    website=lead.website,
                    primary_goal=lead.primary_goal,
                    business_challenges=lead.business_challenges,
                    timeline=lead.timeline,
                    research_summary=result.research.company_summary,
                    personalization=result.personalization
                )
            else:
                dynamic_vars = retell_service.build_minimal_variables(
                    company_name=lead.company_name,
                    email=lead.email,
                    primary_goal=lead.primary_goal,
                    business_challenges=lead.business_challenges
                )

            call_id = await retell_service.create_call(
                to_number=lead.phone,
                dynamic_variables=dynamic_vars,
                metadata={"inquiry_id": inquiry_id, "company_name": lead.company_name}
            )

            if call_id:
                await db_service.update_call_initiated(inquiry_id, call_id)
                logger.info(f"Retell call initiated: {call_id}")
            else:
                await db_service.update_status(inquiry_id, "call_failed")

        logger.info(f"Background processing completed for {inquiry_id}")

    except Exception as e:
        logger.error(f"Background form processing failed: {e}")


# ===========================================
# Retell Webhook - Flow 2 Entry Point
# ===========================================

@router.post(
    "/retell",
    response_model=RetellWebhookResponse,
    status_code=202,
    summary="Process Retell Call Webhook"
)
async def retell_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> RetellWebhookResponse:
    """
    Handle incoming Retell webhook.

    Returns 202 Accepted immediately while post-call processing
    runs in the background.
    """
    try:
        raw_data = await request.json()

        # Handle nested body structure
        if "body" in raw_data and isinstance(raw_data["body"], dict):
            raw_data = raw_data["body"]

        payload = RetellWebhookPayload(**raw_data)

        logger.info(f"Received Retell webhook: event={payload.event}")

        if payload.event != "call_analyzed":
            return RetellWebhookResponse(
                status="ignored",
                message=f"Event '{payload.event}' ignored"
            )

        # Process in background
        background_tasks.add_task(_process_retell_background, payload)

        return RetellWebhookResponse(
            status="accepted",
            message="Retell webhook received - processing in background"
        )

    except Exception as e:
        logger.error(f"Retell webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process: {str(e)}")


async def _process_retell_background(payload: RetellWebhookPayload):
    """Background task for Retell webhook processing."""
    try:
        await lead_processor.process_retell_webhook(payload)
    except Exception as e:
        logger.error(f"Background Retell processing failed: {e}")


# ===========================================
# Status Endpoint
# ===========================================

@router.get(
    "/status/{inquiry_id}",
    summary="Get Inquiry Status"
)
async def get_inquiry_status(inquiry_id: str) -> Dict[str, Any]:
    """Get the current status of an inquiry."""
    try:
        inquiry = await lead_processor.get_inquiry_status(inquiry_id)

        if not inquiry:
            raise HTTPException(status_code=404, detail=f"Inquiry not found: {inquiry_id}")

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
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Test Endpoints
# ===========================================

test_router = APIRouter(prefix="/test", tags=["testing"])


@test_router.post("/pre-call", response_model=TestResponse)
async def test_pre_call(request: Request) -> TestResponse:
    """Test pre-call pipeline without Retell call."""
    try:
        raw_data = await request.json()

        if "body" in raw_data and isinstance(raw_data["body"], dict):
            raw_data = raw_data["body"]

        lead = lead_processor.parse_form_submission(raw_data)

        from src.intelligence.crews.pre_call import PreCallCrew
        crew = PreCallCrew()
        result = await crew.run_async(lead)

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
        return TestResponse(status="error", message=str(e), data={})


@test_router.post("/post-call", response_model=TestResponse)
async def test_post_call(request: Request) -> TestResponse:
    """Test post-call pipeline with sample data."""
    try:
        data = await request.json()

        from src.models import InquiryRecord, LeadStatus
        from datetime import datetime

        inquiry = InquiryRecord(
            id="test-inquiry-id",
            company_name=data.get("company_name", "Test Company"),
            email=data.get("email", "test@test.com"),
            status=LeadStatus.CALL_COMPLETED,
            created_at=datetime.now()
        )

        from src.intelligence.crews.post_call import PostCallCrew
        crew = PostCallCrew()
        result = await crew.run_async(
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
        return TestResponse(status="error", message=str(e), data={})


@test_router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "nodari-sales-engine"}
