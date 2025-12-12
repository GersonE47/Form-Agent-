"""
Nodari Sales Engine - FastAPI Application Entry Point.

Intelligent sales automation system using CrewAI agents for:
- Pre-call intelligence gathering
- Post-call analysis and follow-up

Run with:
    uvicorn src.main:app --reload --port 8000
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.api.webhooks import router as webhook_router, test_router


# ===========================================
# Logging Configuration
# ===========================================

def setup_logging():
    """Configure application logging."""
    settings = get_settings()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()


# ===========================================
# Application Lifespan
# ===========================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()

    logger.info("=" * 50)
    logger.info("Nodari Sales Engine Starting Up")
    logger.info("=" * 50)
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    logger.info(f"Hot threshold: {settings.HOT_THRESHOLD}")
    logger.info(f"Warm threshold: {settings.WARM_THRESHOLD}")

    # Verify critical settings
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning("Supabase credentials not configured!")

    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured!")

    if not settings.RETELL_API_KEY:
        logger.warning("Retell API key not configured!")

    logger.info("Startup complete - ready to accept webhooks")

    yield

    # Shutdown
    logger.info("Nodari Sales Engine shutting down...")


# ===========================================
# FastAPI Application
# ===========================================

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Nodari Sales Engine",
        description="""
        Intelligent sales automation system powered by CrewAI agents.

        ## Features

        - **Pre-Call Intelligence**: Research, scoring, and personalization
        - **AI Voice Calls**: Automated calls via Retell AI
        - **Post-Call Analysis**: Transcript analysis and follow-up routing
        - **Automated Follow-up**: Proposals, meetings, and emails

        ## Webhooks

        - `POST /webhook/form` - Google Form submissions
        - `POST /webhook/retell` - Retell call completion events

        ## Testing

        - `POST /test/pre-call` - Test pre-call pipeline
        - `POST /test/post-call` - Test post-call pipeline
        - `GET /test/health` - Health check
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(webhook_router)
    app.include_router(test_router)

    return app


# Create app instance
app = create_app()


# ===========================================
# Root Endpoint
# ===========================================

@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return JSONResponse({
        "service": "Nodari Sales Engine",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "webhooks": {
                "form": "POST /webhook/form",
                "retell": "POST /webhook/retell",
                "status": "GET /webhook/status/{inquiry_id}"
            },
            "testing": {
                "pre_call": "POST /test/pre-call",
                "post_call": "POST /test/post-call",
                "health": "GET /test/health"
            },
            "docs": "GET /docs"
        }
    })


# ===========================================
# Error Handlers
# ===========================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if get_settings().DEBUG else "An error occurred"
        }
    )


# ===========================================
# Main Entry Point
# ===========================================

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
