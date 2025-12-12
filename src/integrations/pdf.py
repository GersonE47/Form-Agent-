"""PDF generation for proposals."""

import logging
import os
from datetime import datetime
from typing import Optional

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Service for generating PDF documents from markdown.

    Uses WeasyPrint for high-quality PDF rendering.
    """

    def __init__(self):
        """Initialize generator."""
        self._settings = None
        self._output_dir = None

    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def output_dir(self) -> str:
        """Get or create output directory."""
        if self._output_dir is None:
            self._output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "output",
                "proposals"
            )
            os.makedirs(self._output_dir, exist_ok=True)
        return self._output_dir

    def markdown_to_pdf(
        self,
        markdown_content: str,
        company_name: str,
        template_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert markdown content to PDF.

        Args:
            markdown_content: Markdown text to convert
            company_name: Company name for filename
            template_path: Optional CSS template path

        Returns:
            Path to generated PDF or None on failure
        """
        try:
            import markdown
            from weasyprint import HTML, CSS

            # Convert markdown to HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=["tables", "fenced_code", "toc"]
            )

            # Wrap in HTML document
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Proposal for {company_name}</title>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Load CSS
            css_path = template_path or os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "templates",
                "proposal_style.css"
            )

            stylesheets = []
            if os.path.exists(css_path):
                stylesheets.append(CSS(filename=css_path))

            # Generate filename
            safe_name = "".join(c if c.isalnum() else "_" for c in company_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"proposal_{safe_name}_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, filename)

            # Generate PDF
            HTML(string=full_html).write_pdf(
                output_path,
                stylesheets=stylesheets
            )

            logger.info(f"Generated PDF: {output_path}")
            return output_path

        except ImportError as e:
            logger.error(f"Missing dependency for PDF generation: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            return None

    def generate_proposal_pdf(
        self,
        proposal: "ProposalContent",
        company_name: str
    ) -> Optional[str]:
        """
        Generate PDF from ProposalContent model.

        Args:
            proposal: ProposalContent with all sections
            company_name: Company name

        Returns:
            Path to generated PDF
        """
        return self.markdown_to_pdf(
            proposal.markdown_content,
            company_name
        )


# Forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models import ProposalContent

# Singleton instance
pdf_generator = PDFGenerator()
