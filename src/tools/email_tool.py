"""Gmail email sending tool."""

import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Gmail service for sending emails.

    Uses a service account with domain-wide delegation to
    send emails on behalf of the organization.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send"
    ]

    def __init__(self):
        """Initialize Gmail client."""
        settings = get_settings()
        self.sender_email = settings.GOOGLE_CALENDAR_ID  # Same as calendar owner
        self.credentials_path = settings.GOOGLE_CREDENTIALS_PATH

        # Initialize service
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Gmail API service."""
        try:
            creds_path = Path(self.credentials_path)
            if not creds_path.exists():
                logger.warning(
                    f"Google credentials file not found: {self.credentials_path}. "
                    "Email features will be disabled."
                )
                return

            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                str(creds_path),
                scopes=self.SCOPES
            )

            # Impersonate the sender (requires domain-wide delegation)
            credentials = credentials.with_subject(self.sender_email)

            # Build Gmail service
            self.service = build("gmail", "v1", credentials=credentials)
            logger.info(f"Gmail service initialized for {self.sender_email}")

        except Exception as e:
            logger.error(f"Failed to initialize Gmail: {e}")
            self.service = None

    def is_available(self) -> bool:
        """Check if email service is available."""
        return self.service is not None

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        """
        Send an email with optional PDF attachment.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML email body
            attachment_path: Optional path to PDF attachment

        Returns:
            True if sent successfully
        """
        if not self.service:
            logger.error("Gmail service not initialized")
            return False

        try:
            # Create message
            message = MIMEMultipart()
            message["to"] = to_email
            message["from"] = self.sender_email
            message["subject"] = subject

            # Add HTML body
            html_part = MIMEText(body_html, "html")
            message.attach(html_part)

            # Add attachment if provided
            if attachment_path:
                attachment_file = Path(attachment_path)
                if attachment_file.exists():
                    with open(attachment_file, "rb") as f:
                        pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                        pdf_attachment.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=attachment_file.name
                        )
                        message.attach(pdf_attachment)
                else:
                    logger.warning(f"Attachment not found: {attachment_path}")

            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            self.service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except HttpError as e:
            logger.error(f"Gmail API error sending to {to_email}: {e}")
            return False
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
        """
        Send HOT lead email with proposal and meeting confirmation.

        Args:
            to_email: Recipient email
            company_name: Company name
            contact_name: Contact person name
            meeting_link: Google Calendar meeting link
            proposal_path: Path to proposal PDF

        Returns:
            True if sent successfully
        """
        subject = f"{contact_name}, Your Custom AI Proposal from Nodari"

        meeting_section = ""
        if meeting_link:
            meeting_section = f"""
            <p><strong>Your meeting has been confirmed:</strong></p>
            <p style="margin: 20px 0;">
                <a href="{meeting_link}"
                   style="background-color: #007bff; color: white;
                          padding: 12px 24px; text-decoration: none;
                          border-radius: 5px; font-weight: bold;">
                    Join Meeting
                </a>
            </p>
            """

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h2 style="color: #007bff; margin-top: 0;">Thank you for your interest in Nodari AI!</h2>

                <p>Hi {contact_name},</p>

                <p>It was great speaking with you about {company_name}'s AI initiatives.
                As promised, I've attached a customized proposal outlining how we can help
                you achieve your goals.</p>

                {meeting_section}

                <p>Please review the attached proposal before our call. I'm excited to
                dive deeper into how AI can transform your operations.</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>The Nodari AI Team</strong>
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                <p style="font-size: 12px; color: #666;">
                    Nodari AI | Custom AI Solutions<br>
                    <a href="https://nodari.ai" style="color: #007bff;">nodari.ai</a>
                </p>
            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, body, proposal_path)

    def send_warm_lead_email(
        self,
        to_email: str,
        company_name: str,
        contact_name: str,
        case_study_link: str = "https://nodari.ai/case-studies"
    ) -> bool:
        """
        Send WARM lead email with case study.

        Args:
            to_email: Recipient email
            company_name: Company name
            contact_name: Contact person name
            case_study_link: Link to relevant case study

        Returns:
            True if sent successfully
        """
        subject = f"{contact_name}, See How Companies Like {company_name} Succeed with AI"

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h2 style="color: #28a745; margin-top: 0;">Thank you for exploring AI with Nodari!</h2>

                <p>Hi {contact_name},</p>

                <p>Thank you for taking the time to discuss {company_name}'s AI journey.
                I wanted to share a relevant case study that shows how similar companies
                have achieved remarkable results.</p>

                <p style="margin: 20px 0;">
                    <a href="{case_study_link}"
                       style="background-color: #28a745; color: white;
                              padding: 12px 24px; text-decoration: none;
                              border-radius: 5px; font-weight: bold;">
                        View Case Study
                    </a>
                </p>

                <p>When you're ready to take the next step, I'm here to help you build
                a custom AI solution that fits your unique needs.</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>The Nodari AI Team</strong>
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                <p style="font-size: 12px; color: #666;">
                    Nodari AI | Custom AI Solutions<br>
                    <a href="https://nodari.ai" style="color: #007bff;">nodari.ai</a>
                </p>
            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, body)

    def send_nurture_email(
        self,
        to_email: str,
        contact_name: str
    ) -> bool:
        """
        Send NURTURE lead email with educational content.

        Args:
            to_email: Recipient email
            contact_name: Contact person name

        Returns:
            True if sent successfully
        """
        subject = f"{contact_name}, Your Guide to Getting Started with AI"

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h2 style="color: #6c757d; margin-top: 0;">Start Your AI Journey with Nodari</h2>

                <p>Hi {contact_name},</p>

                <p>Thank you for your interest in AI solutions. We understand that
                exploring AI can feel overwhelming, so we've put together some
                resources to help you get started.</p>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #333;">Helpful Resources:</h3>
                    <ul style="padding-left: 20px;">
                        <li><a href="https://nodari.ai/blog/ai-for-business" style="color: #007bff;">Understanding AI for Business: A Beginner's Guide</a></li>
                        <li><a href="https://nodari.ai/blog/ai-readiness" style="color: #007bff;">5 Signs Your Business is Ready for AI</a></li>
                        <li><a href="https://nodari.ai/blog/ai-roi" style="color: #007bff;">How to Calculate AI ROI</a></li>
                    </ul>
                </div>

                <p>When you're ready to explore further, we're here to help!</p>

                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>The Nodari AI Team</strong>
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                <p style="font-size: 12px; color: #666;">
                    Nodari AI | Custom AI Solutions<br>
                    <a href="https://nodari.ai" style="color: #007bff;">nodari.ai</a>
                </p>
            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, body)


# ===========================================
# Singleton Instance
# ===========================================

email_service = EmailService()
