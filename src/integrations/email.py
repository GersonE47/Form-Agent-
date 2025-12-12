"""Gmail integration for sending follow-up emails."""

import logging
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails via Gmail API.

    Uses service account with domain-wide delegation.
    """

    def __init__(self):
        """Initialize service."""
        self._service = None
        self._settings = None
        self._available = None

    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def service(self):
        """Lazy initialize Gmail service."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        """Build Gmail service with service account."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials_path = self.settings.GOOGLE_CREDENTIALS_PATH

            if not os.path.exists(credentials_path):
                logger.warning(f"Google credentials not found: {credentials_path}")
                return None

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/gmail.send"]
            )

            # Delegate to email sender
            delegated_credentials = credentials.with_subject(
                self.settings.GOOGLE_CALENDAR_ID
            )

            service = build("gmail", "v1", credentials=delegated_credentials)
            logger.info("Gmail service initialized")
            return service

        except ImportError:
            logger.error("google-api-python-client not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            return None

    def is_available(self) -> bool:
        """Check if email service is available."""
        if self._available is None:
            self._available = self.service is not None
        return self._available

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        """
        Internal method to send email.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML email body
            attachment_path: Optional file attachment

        Returns:
            True if sent successfully
        """
        if not self.is_available():
            logger.warning("Email service not available")
            return False

        try:
            message = MIMEMultipart()
            message["to"] = to_email
            message["from"] = self.settings.GOOGLE_CALENDAR_ID
            message["subject"] = subject

            message.attach(MIMEText(html_body, "html"))

            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, "rb") as f:
                    attachment = MIMEApplication(f.read(), _subtype="pdf")
                    attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=os.path.basename(attachment_path)
                    )
                    message.attach(attachment)

            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_hot_lead_email(
        self,
        to_email: str,
        company_name: str,
        contact_name: str,
        meeting_link: Optional[str] = None,
        proposal_path: Optional[str] = None
    ) -> bool:
        """Send hot lead follow-up with proposal."""
        meeting_section = ""
        if meeting_link:
            meeting_section = f"""
            <p><strong>Your Meeting is Confirmed!</strong></p>
            <p>Join here: <a href="{meeting_link}">{meeting_link}</a></p>
            <hr>
            """

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Hi {contact_name},</p>

            <p>Thank you for the great conversation! I'm excited about the potential
            to help {company_name} with your AI initiatives.</p>

            {meeting_section}

            <p>As promised, I've attached a proposal outlining our recommended approach.
            Please take a look and let me know if you have any questions.</p>

            <p><strong>Key highlights:</strong></p>
            <ul>
                <li>Custom AI solution tailored to your needs</li>
                <li>Proven implementation methodology</li>
                <li>Dedicated support throughout the project</li>
            </ul>

            <p>Looking forward to our next conversation!</p>

            <p>Best regards,<br>
            <strong>Nodari AI Team</strong><br>
            <a href="https://nodari.ai">nodari.ai</a></p>
        </body>
        </html>
        """

        return self._send_email(
            to_email=to_email,
            subject=f"Your AI Proposal - {company_name} x Nodari AI",
            html_body=html,
            attachment_path=proposal_path
        )

    def send_warm_lead_email(
        self,
        to_email: str,
        company_name: str,
        contact_name: str,
        case_study_link: str = "https://nodari.ai/case-studies"
    ) -> bool:
        """Send warm lead follow-up with case study."""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Hi {contact_name},</p>

            <p>Thank you for taking the time to speak with me about {company_name}'s
            AI initiatives. I enjoyed learning about your goals.</p>

            <p>I thought you might find this case study interesting - it covers how
            we helped a company in a similar situation achieve significant results:</p>

            <p style="text-align: center; margin: 20px 0;">
                <a href="{case_study_link}"
                   style="background-color: #2563eb; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Case Study
                </a>
            </p>

            <p>When you're ready to explore how we might help {company_name},
            I'd be happy to set up a follow-up discussion.</p>

            <p>Best regards,<br>
            <strong>Nodari AI Team</strong><br>
            <a href="https://nodari.ai">nodari.ai</a></p>
        </body>
        </html>
        """

        return self._send_email(
            to_email=to_email,
            subject=f"AI Success Story - Thought You'd Find This Interesting",
            html_body=html
        )

    def send_nurture_email(
        self,
        to_email: str,
        contact_name: str
    ) -> bool:
        """Send nurture sequence email."""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Hi {contact_name},</p>

            <p>Thanks for your interest in Nodari AI. I wanted to share some
            resources that might be helpful as you explore AI solutions:</p>

            <p><strong>Popular Resources:</strong></p>
            <ul>
                <li><a href="https://nodari.ai/blog/ai-implementation-guide">
                    AI Implementation Guide for Business Leaders</a></li>
                <li><a href="https://nodari.ai/blog/ai-roi-calculator">
                    How to Calculate AI ROI</a></li>
                <li><a href="https://nodari.ai/case-studies">
                    Customer Success Stories</a></li>
            </ul>

            <p>If you ever want to discuss how AI might help your business,
            I'm happy to chat - no pressure.</p>

            <p>Best regards,<br>
            <strong>Nodari AI Team</strong><br>
            <a href="https://nodari.ai">nodari.ai</a></p>
        </body>
        </html>
        """

        return self._send_email(
            to_email=to_email,
            subject="Resources for Your AI Journey",
            html_body=html
        )


# Singleton instance
email_service = EmailService()
