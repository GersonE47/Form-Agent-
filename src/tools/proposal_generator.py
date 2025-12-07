"""Proposal generation tool - Markdown to PDF conversion."""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import markdown
from jinja2 import Template

from src.config import get_settings

logger = logging.getLogger(__name__)


class ProposalGenerator:
    """
    Proposal generator that converts markdown to PDF.

    Uses markdown and weasyprint to generate professional
    PDF proposals from markdown content.
    """

    def __init__(self):
        """Initialize proposal generator."""
        self.template_dir = Path("templates")
        self.output_dir = Path("output/proposals")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Proposal generator initialized - output: {self.output_dir}")

    def load_template(self) -> str:
        """Load the proposal markdown template."""
        template_path = self.template_dir / "proposal_template.md"

        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        else:
            # Return default template if file doesn't exist
            return self._get_default_template()

    def load_css(self) -> str:
        """Load CSS styles for PDF generation."""
        css_path = self.template_dir / "proposal_style.css"

        if css_path.exists():
            return css_path.read_text(encoding="utf-8")
        else:
            return self._get_default_css()

    def render_proposal(
        self,
        company_name: str,
        contact_name: str,
        executive_summary: str,
        problem_statement: str,
        proposed_solution: str,
        timeline: str,
        investment: str,
        next_steps: str,
        case_studies: Optional[list] = None
    ) -> str:
        """
        Render proposal from template with provided content.

        Args:
            company_name: Target company name
            contact_name: Contact person name
            executive_summary: Executive summary content
            problem_statement: Problem/challenges description
            proposed_solution: Proposed solution description
            timeline: Implementation timeline
            investment: Investment/pricing information
            next_steps: Next steps and CTA
            case_studies: Optional list of relevant case studies

        Returns:
            Rendered markdown content
        """
        template_content = self.load_template()
        template = Template(template_content)

        rendered = template.render(
            company_name=company_name,
            contact_name=contact_name,
            date=datetime.now().strftime("%B %d, %Y"),
            executive_summary=executive_summary,
            problem_statement=problem_statement,
            proposed_solution=proposed_solution,
            timeline=timeline,
            investment=investment,
            next_steps=next_steps,
            case_studies=case_studies or []
        )

        return rendered

    def markdown_to_pdf(
        self,
        markdown_content: str,
        company_name: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Convert markdown proposal to PDF.

        Args:
            markdown_content: Markdown content to convert
            company_name: Company name for filename
            filename: Optional custom filename

        Returns:
            Path to generated PDF file
        """
        try:
            # Import weasyprint here to handle missing dependency gracefully
            from weasyprint import HTML, CSS

            # Convert markdown to HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=[
                    "tables",
                    "fenced_code",
                    "toc",
                    "nl2br"
                ]
            )

            # Load CSS
            css_content = self.load_css()

            # Wrap in full HTML document
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AI Solutions Proposal - {company_name}</title>
                <style>
                    {css_content}
                </style>
            </head>
            <body>
                <div class="proposal-content">
                    {html_content}
                </div>
            </body>
            </html>
            """

            # Generate filename
            if filename:
                safe_filename = filename
            else:
                safe_name = "".join(
                    c if c.isalnum() else "_"
                    for c in company_name
                )
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"proposal_{safe_name}_{timestamp}.pdf"

            output_path = self.output_dir / safe_filename

            # Generate PDF
            html_doc = HTML(string=full_html)
            html_doc.write_pdf(str(output_path))

            logger.info(f"Proposal PDF generated: {output_path}")
            return str(output_path)

        except ImportError:
            logger.error(
                "weasyprint not installed. Install with: pip install weasyprint"
            )
            # Fallback: save markdown file instead
            return self._save_markdown_fallback(markdown_content, company_name)

        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            # Fallback to markdown
            return self._save_markdown_fallback(markdown_content, company_name)

    def _save_markdown_fallback(
        self,
        markdown_content: str,
        company_name: str
    ) -> str:
        """Save markdown file as fallback when PDF generation fails."""
        safe_name = "".join(c if c.isalnum() else "_" for c in company_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"proposal_{safe_name}_{timestamp}.md"
        output_path = self.output_dir / filename

        output_path.write_text(markdown_content, encoding="utf-8")
        logger.info(f"Proposal saved as markdown (PDF fallback): {output_path}")

        return str(output_path)

    def _get_default_template(self) -> str:
        """Get default proposal template."""
        return """# Custom AI Solutions Proposal

**Prepared for:** {{ company_name }}
**Prepared by:** Nodari AI
**Date:** {{ date }}

---

## Executive Summary

{{ executive_summary }}

---

## Understanding Your Challenges

{{ problem_statement }}

---

## Proposed Solution

{{ proposed_solution }}

---

## Implementation Timeline

{{ timeline }}

---

## Investment

{{ investment }}

---

## Next Steps

{{ next_steps }}

{% if case_studies %}
---

## Relevant Case Studies

{% for case_study in case_studies %}
- {{ case_study }}
{% endfor %}
{% endif %}

---

## About Nodari AI

Nodari AI specializes in building custom AI solutions that drive real business results.
Our team of experts combines deep technical knowledge with business acumen to deliver
solutions that transform operations and create competitive advantages.

**Contact Us:**
- Website: [nodari.ai](https://nodari.ai)
- Email: contact@nodari.ai

---

*This proposal is confidential and intended solely for {{ company_name }}.*
"""

    def _get_default_css(self) -> str:
        """Get default CSS for PDF styling."""
        return """
        @page {
            size: letter;
            margin: 1in;
            @top-right {
                content: "Nodari AI | Confidential";
                font-size: 10px;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }

        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }

        .proposal-content {
            max-width: 100%;
        }

        h1 {
            color: #007bff;
            font-size: 24pt;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 3px solid #007bff;
        }

        h2 {
            color: #333;
            font-size: 16pt;
            margin-top: 25px;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 1px solid #ddd;
        }

        h3 {
            color: #555;
            font-size: 13pt;
            margin-top: 20px;
        }

        p {
            margin-bottom: 12px;
            text-align: justify;
        }

        ul, ol {
            margin-bottom: 15px;
            padding-left: 25px;
        }

        li {
            margin-bottom: 8px;
        }

        strong {
            color: #007bff;
        }

        hr {
            border: none;
            border-top: 1px solid #ddd;
            margin: 30px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }

        th {
            background-color: #007bff;
            color: white;
        }

        tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        a {
            color: #007bff;
            text-decoration: none;
        }

        blockquote {
            border-left: 4px solid #007bff;
            margin: 20px 0;
            padding: 10px 20px;
            background-color: #f8f9fa;
            font-style: italic;
        }

        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
        }
        """


# ===========================================
# Singleton Instance
# ===========================================

proposal_generator = ProposalGenerator()
