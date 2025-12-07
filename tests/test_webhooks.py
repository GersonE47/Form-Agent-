"""Tests for webhook API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


class TestFormWebhook:
    """Tests for POST /webhook/form endpoint."""

    def test_form_webhook_success(self, client: TestClient, sample_form_data):
        """Test successful form submission processing."""
        with patch("src.services.lead_processor.lead_processor.process_form_webhook") as mock_process:
            mock_process.return_value = "inq_test_12345"

            response = client.post("/webhook/form", json=sample_form_data)

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            assert data["inquiry_id"] == "inq_test_12345"
            assert "message" in data

    def test_form_webhook_with_nested_body(self, client: TestClient, sample_form_data):
        """Test form submission with nested body structure."""
        with patch("src.services.lead_processor.lead_processor.process_form_webhook") as mock_process:
            mock_process.return_value = "inq_test_12345"

            # Wrap data in body (as Apps Script might send)
            nested_data = {"body": sample_form_data}
            response = client.post("/webhook/form", json=nested_data)

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"

    def test_form_webhook_minimal_data(self, client: TestClient, sample_form_data_minimal):
        """Test form submission with minimal data."""
        with patch("src.services.lead_processor.lead_processor.process_form_webhook") as mock_process:
            mock_process.return_value = "inq_test_12345"

            response = client.post("/webhook/form", json=sample_form_data_minimal)

            assert response.status_code == 202

    def test_form_webhook_missing_email(self, client: TestClient):
        """Test form submission fails without email."""
        response = client.post("/webhook/form", json={"Name ": "Test Company"})

        assert response.status_code == 400
        assert "Email" in response.json()["detail"]

    def test_form_webhook_processing_error(self, client: TestClient, sample_form_data):
        """Test form submission handles processing errors."""
        with patch("src.services.lead_processor.lead_processor.process_form_webhook") as mock_process:
            mock_process.side_effect = Exception("Database error")

            response = client.post("/webhook/form", json=sample_form_data)

            assert response.status_code == 500
            assert "Failed to process" in response.json()["detail"]


class TestRetellWebhook:
    """Tests for POST /webhook/retell endpoint."""

    def test_retell_webhook_call_analyzed(
        self,
        client: TestClient,
        sample_retell_webhook_call_analyzed
    ):
        """Test successful call_analyzed webhook processing."""
        with patch("src.services.lead_processor.lead_processor.process_retell_webhook") as mock_process:
            mock_process.return_value = None

            response = client.post(
                "/webhook/retell",
                json=sample_retell_webhook_call_analyzed
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            assert "processing started" in data["message"]

    def test_retell_webhook_with_nested_body(
        self,
        client: TestClient,
        sample_retell_webhook_call_analyzed
    ):
        """Test Retell webhook with nested body structure."""
        with patch("src.services.lead_processor.lead_processor.process_retell_webhook") as mock_process:
            mock_process.return_value = None

            nested_data = {"body": sample_retell_webhook_call_analyzed}
            response = client.post("/webhook/retell", json=nested_data)

            assert response.status_code == 202

    def test_retell_webhook_ignores_call_started(
        self,
        client: TestClient,
        sample_retell_webhook_call_started
    ):
        """Test that non-analyzed events are ignored."""
        response = client.post(
            "/webhook/retell",
            json=sample_retell_webhook_call_started
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "ignored"
        assert "call_started" in data["message"]

    def test_retell_webhook_processing_error(
        self,
        client: TestClient,
        sample_retell_webhook_call_analyzed
    ):
        """Test Retell webhook handles processing errors gracefully."""
        with patch("src.services.lead_processor.lead_processor.process_retell_webhook") as mock_process:
            # Error happens in background, webhook still returns 202
            mock_process.side_effect = Exception("Database error")

            response = client.post(
                "/webhook/retell",
                json=sample_retell_webhook_call_analyzed
            )

            # Should still accept the webhook
            assert response.status_code == 202


class TestStatusEndpoint:
    """Tests for GET /webhook/status/{inquiry_id} endpoint."""

    def test_get_status_success(self, client: TestClient):
        """Test successful status retrieval."""
        from src.models import InquiryRecord, LeadStatus
        from datetime import datetime

        mock_inquiry = InquiryRecord(
            id="inq_test_12345",
            company_name="Test Company",
            email="test@test.com",
            status=LeadStatus.CALL_COMPLETED,
            lead_score=75,
            lead_category="hot",
            retell_call_id="call_123",
            meeting_booked=True,
            created_at=datetime.now()
        )

        with patch("src.services.lead_processor.lead_processor.get_inquiry_status") as mock_get:
            mock_get.return_value = mock_inquiry

            response = client.get("/webhook/status/inq_test_12345")

            assert response.status_code == 200
            data = response.json()
            assert data["inquiry_id"] == "inq_test_12345"
            assert data["company_name"] == "Test Company"
            assert data["status"] == "call_completed"
            assert data["lead_score"] == 75
            assert data["meeting_booked"] is True

    def test_get_status_not_found(self, client: TestClient):
        """Test status retrieval for non-existent inquiry."""
        with patch("src.services.lead_processor.lead_processor.get_inquiry_status") as mock_get:
            mock_get.return_value = None

            response = client.get("/webhook/status/nonexistent_id")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"]


class TestTestEndpoints:
    """Tests for /test/* endpoints."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/test/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nodari-sales-engine"

    def test_pre_call_test_endpoint(self, client: TestClient, sample_form_data):
        """Test pre-call pipeline test endpoint."""
        with patch("src.crews.pre_call_crew.PreCallCrew") as mock_crew_class:
            from src.models import PreCallResult

            mock_crew = mock_crew_class.return_value
            mock_crew.run.return_value = PreCallResult(success=True)

            response = client.post("/test/pre-call", json=sample_form_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "partial"]

    def test_post_call_test_endpoint(self, client: TestClient, sample_transcript):
        """Test post-call pipeline test endpoint."""
        with patch("src.crews.post_call_crew.PostCallCrew") as mock_crew_class:
            from src.models import PostCallResult

            mock_crew = mock_crew_class.return_value
            mock_crew.run.return_value = PostCallResult(success=True)

            payload = {
                "transcript": sample_transcript,
                "call_summary": "Test summary",
                "company_name": "Test Company",
                "email": "test@test.com"
            }

            response = client.post("/test/post-call", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "partial", "error"]


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Nodari Sales Engine"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "webhooks" in data["endpoints"]
        assert "form" in data["endpoints"]["webhooks"]
        assert "retell" in data["endpoints"]["webhooks"]


class TestFieldMapping:
    """Tests for Google Form field mapping."""

    def test_field_mapping_with_trailing_spaces(self, client: TestClient):
        """Test that field names with trailing spaces are handled."""
        from src.config import map_form_fields

        raw_data = {
            "Name ": "Test Company",  # Note trailing space
            "Email": "test@test.com",
            "Phone Number ": "+1234567890",  # Note trailing space
            "Website ": "https://test.com"  # Note trailing space
        }

        mapped = map_form_fields(raw_data)

        assert mapped["company_name"] == "Test Company"
        assert mapped["email"] == "test@test.com"
        assert mapped["phone"] == "+1234567890"
        assert mapped["website"] == "https://test.com"

    def test_field_mapping_preserves_unmapped_fields(self):
        """Test that unmapped fields are preserved."""
        from src.config import map_form_fields

        raw_data = {
            "Email": "test@test.com",
            "custom_field": "custom_value"
        }

        mapped = map_form_fields(raw_data)

        assert mapped["email"] == "test@test.com"
        assert mapped["custom_field"] == "custom_value"


class TestPhoneFormatting:
    """Tests for phone number formatting."""

    def test_phone_formatting_us_number(self):
        """Test US phone number formatting."""
        from src.config import format_phone_number

        assert format_phone_number("4155551234") == "+14155551234"
        assert format_phone_number("14155551234") == "+14155551234"
        assert format_phone_number("+14155551234") == "+14155551234"

    def test_phone_formatting_with_formatting(self):
        """Test phone formatting removes non-digits."""
        from src.config import format_phone_number

        assert format_phone_number("(415) 555-1234") == "+14155551234"
        assert format_phone_number("415-555-1234") == "+14155551234"
        assert format_phone_number("415.555.1234") == "+14155551234"

    def test_phone_formatting_empty(self):
        """Test phone formatting handles empty input."""
        from src.config import format_phone_number

        assert format_phone_number("") is None
        assert format_phone_number(None) is None


# ===========================================
# Integration Tests (marked for selective running)
# ===========================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests that require real services."""

    @pytest.mark.slow
    def test_full_form_flow(self, client_no_mocks: TestClient, sample_form_data):
        """Test complete form submission flow."""
        # This would test with real services
        # Skip if credentials not available
        pytest.skip("Requires real service credentials")

    @pytest.mark.slow
    def test_full_retell_flow(
        self,
        client_no_mocks: TestClient,
        sample_retell_webhook_call_analyzed
    ):
        """Test complete Retell webhook flow."""
        # This would test with real services
        pytest.skip("Requires real service credentials")
