"""Pytest fixtures and configuration for Nodari Sales Engine tests."""

import os
import pytest
from datetime import datetime
from typing import Dict, Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("RETELL_API_KEY", "key_test")
os.environ.setdefault("RETELL_AGENT_ID", "agent_test")
os.environ.setdefault("RETELL_FROM_NUMBER", "+18001234567")
os.environ.setdefault("FIRECRAWL_API_KEY", "fc-test")
os.environ.setdefault("DEBUG", "true")


# ===========================================
# Sample Data Fixtures
# ===========================================

@pytest.fixture
def sample_form_data() -> Dict[str, Any]:
    """Sample Google Form submission data."""
    return {
        "Name ": "Test Company Inc",
        "Email": "test@testcompany.com",
        "Phone Number ": "+14155551234",
        "Website ": "https://testcompany.com",
        "What is your primary goal for implementing a custom AI system?": "Automate customer support",
        "Please briefly describe the key business processes or challenges you are looking to address with AI.": "We have a high volume of customer inquiries and want to reduce response times while maintaining quality.",
        "Which of the following data sources are most relevant to your potential AI system?": "CRM data, Customer support tickets",
        "On a scale of 1 to 5, how critical is it for the AI system to operate entirely within your existing infrastructure?": "4",
        "What is your estimated timeline for launching a custom AI solution?": "3-6 months",
        "What date and time would you prefer for a follow-up discussion?": "Next Tuesday at 2pm",
        "formId": "test-form-123",
        "submittedAt": datetime.now().isoformat()
    }


@pytest.fixture
def sample_form_data_minimal() -> Dict[str, Any]:
    """Minimal form data with only required fields."""
    return {
        "Name ": "Minimal Corp",
        "Email": "minimal@test.com"
    }


@pytest.fixture
def sample_retell_webhook_call_analyzed() -> Dict[str, Any]:
    """Sample Retell webhook payload for call_analyzed event."""
    return {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_test_12345",
            "agent_id": "agent_test",
            "call_type": "outbound",
            "from_number": "+18001234567",
            "to_number": "+14155551234",
            "direction": "outbound",
            "call_status": "ended",
            "start_timestamp": 1700000000000,
            "end_timestamp": 1700000300000,
            "transcript": """
Agent: Hi, this is Alex from Nodari AI. Am I speaking with someone from Test Company?
Customer: Yes, this is John.
Agent: Great! Thanks for taking my call, John. I understand you're looking to automate customer support with AI. Can you tell me more about your current challenges?
Customer: Sure. We get about 500 support tickets a day and our team is overwhelmed. Response times are suffering.
Agent: That sounds frustrating. With 500 tickets daily, I can see how that would strain your team. What's your current average response time?
Customer: Usually about 24 hours, but customers expect faster responses these days.
Agent: Absolutely. Our AI solutions typically help reduce response times by 60-80%. Would you be interested in seeing a demo of how this could work for your specific use case?
Customer: Yes, I think that would be helpful. When could we do that?
Agent: How about Thursday at 10am? Does that work for you?
Customer: Thursday at 10am works. Let me check... yes, I can make that.
Agent: Perfect. I'll send you a calendar invite. Before I go, is there anyone else from your team who should join the demo?
Customer: I should bring our VP of Customer Success, Sarah. She'd want to see this.
Agent: Great. I'll include her in the invite if you can share her email. Looking forward to Thursday!
Customer: Sounds good, thanks Alex!
            """,
            "recording_url": "https://storage.retell.ai/recordings/call_test_12345.wav",
            "call_length_sec": 180,
            "call_analysis": {
                "call_summary": "Positive discovery call. Customer confirmed pain point of high ticket volume and slow response times. Agreed to demo on Thursday at 10am. Will bring VP of Customer Success.",
                "sentiment": "positive"
            }
        }
    }


@pytest.fixture
def sample_retell_webhook_call_started() -> Dict[str, Any]:
    """Sample Retell webhook for call_started event."""
    return {
        "event": "call_started",
        "call": {
            "call_id": "call_test_12345",
            "agent_id": "agent_test",
            "call_status": "ongoing"
        }
    }


@pytest.fixture
def sample_inquiry_record() -> Dict[str, Any]:
    """Sample inquiry record from database."""
    return {
        "id": "inq_test_12345",
        "company_name": "Test Company Inc",
        "email": "test@testcompany.com",
        "phone": "+14155551234",
        "website": "https://testcompany.com",
        "primary_goal": "Automate customer support",
        "business_challenges": "High volume of customer inquiries",
        "data_sources": "CRM data, Customer support tickets",
        "infrastructure_criticality": 4,
        "timeline": "3-6 months",
        "preferred_datetime": "Next Tuesday at 2pm",
        "status": "new",
        "lead_score": None,
        "lead_category": None,
        "retell_call_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": None
    }


@pytest.fixture
def sample_transcript() -> str:
    """Sample call transcript for testing analysis."""
    return """
Agent: Hi, this is Alex from Nodari AI. Am I speaking with someone from Test Company?
Customer: Yes, this is John from Test Company.
Agent: Great to connect with you, John! I saw you filled out our form about AI automation. What's driving your interest?
Customer: We're drowning in customer support tickets. Our team is burned out and customers are complaining about slow responses.
Agent: I hear that a lot. How many tickets are you dealing with daily?
Customer: Around 500, sometimes more. And our team of 10 can't keep up.
Agent: That's a significant volume. What's your current average response time?
Customer: About 24 hours, which is way too slow. Our competitors respond in under 4 hours.
Agent: I understand the pressure. Our AI solutions typically help companies reduce response times by 60-80%. Would you have budget set aside for a solution like this?
Customer: Yes, we've allocated around $50,000 for this initiative. Is that in the right ballpark?
Agent: That's definitely a good starting point for what you're describing. Who would be the decision maker for a project like this?
Customer: That would be me, along with our CTO who would handle the technical evaluation.
Agent: Perfect. Would it make sense to schedule a demo where your CTO could join? Maybe Thursday at 10am?
Customer: Thursday at 10am works. I'll check with Sarah - she's the CTO - but I think that should work.
Agent: Excellent! I'll send over a calendar invite. Is there anything specific you'd like us to cover in the demo?
Customer: Mainly how the AI handles complex tickets and integrates with our existing Zendesk setup.
Agent: Great questions - we'll definitely cover both. Looking forward to Thursday!
    """


# ===========================================
# Mock Fixtures
# ===========================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("src.database.supabase") as mock:
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "inq_test_12345"}
        ]
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "inq_test_12345", "company_name": "Test Company"}
        ]
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "inq_test_12345"}
        ]
        yield mock


@pytest.fixture
def mock_retell():
    """Mock Retell API client."""
    with patch("src.tools.retell_caller.httpx.AsyncClient") as mock:
        mock_instance = AsyncMock()
        mock_instance.post.return_value.status_code = 201
        mock_instance.post.return_value.json.return_value = {
            "call_id": "call_test_12345",
            "status": "queued"
        }
        mock.return_value.__aenter__.return_value = mock_instance
        mock.return_value.__aexit__.return_value = None
        yield mock


@pytest.fixture
def mock_firecrawl():
    """Mock Firecrawl API client."""
    with patch("src.tools.web_scraper.FirecrawlApp") as mock:
        mock_instance = MagicMock()
        mock_instance.scrape_url.return_value = {
            "markdown": "# Test Company\n\nWe are a leading provider of...",
            "metadata": {"title": "Test Company - Home"}
        }
        mock_instance.search.return_value = [
            {"title": "Test Company announces...", "url": "https://news.com/test"}
        ]
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar API."""
    with patch("src.tools.calendar_tool.build") as mock:
        mock_service = MagicMock()
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "event_test_123",
            "htmlLink": "https://calendar.google.com/event?id=event_test_123"
        }
        mock_service.freebusy.return_value.query.return_value.execute.return_value = {
            "calendars": {"test@example.com": {"busy": []}}
        }
        mock.return_value = mock_service
        yield mock


@pytest.fixture
def mock_gmail():
    """Mock Gmail API."""
    with patch("src.tools.email_tool.build") as mock:
        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "msg_test_123",
            "labelIds": ["SENT"]
        }
        mock.return_value = mock_service
        yield mock


# ===========================================
# Client Fixtures
# ===========================================

@pytest.fixture
def client(
    mock_supabase,
    mock_retell,
    mock_firecrawl,
    mock_google_calendar,
    mock_gmail
) -> Generator[TestClient, None, None]:
    """Test client with all external services mocked."""
    from src.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_no_mocks() -> Generator[TestClient, None, None]:
    """Test client without mocks (for integration tests)."""
    from src.main import app
    with TestClient(app) as test_client:
        yield test_client


# ===========================================
# Pytest Configuration
# ===========================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    yield
    # Clean up any singleton state if needed
