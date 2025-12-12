"""Proposal-related models."""

from typing import Optional, List
from pydantic import BaseModel, Field


class ProposalContent(BaseModel):
    """Generated proposal content from the Proposal Agent."""
    executive_summary: str = Field(
        ...,
        description="Executive summary section"
    )
    problem_statement: str = Field(
        ...,
        description="Understanding of client's challenges"
    )
    proposed_solution: str = Field(
        ...,
        description="Proposed AI solution description"
    )
    timeline: str = Field(
        ...,
        description="Implementation timeline"
    )
    investment: str = Field(
        ...,
        description="Investment/pricing section"
    )
    next_steps: str = Field(
        ...,
        description="Recommended next steps"
    )
    case_studies: List[str] = Field(
        default_factory=list,
        description="Relevant case study references"
    )
    markdown_content: str = Field(
        ...,
        description="Complete proposal in Markdown format"
    )
