"""Ticket input model."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Ticket(BaseModel):
    """Input ticket that drives the entire PQC pipeline."""

    title: str = Field(..., min_length=5, description="Short title of the change")
    description: str = Field(..., min_length=20, description="Detailed description of what is needed")
    repo_url: Optional[str] = Field(None, description="Git repository URL (optional for local mode)")
    base_branch: str = Field("main", description="Base branch to work from")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of measurable acceptance criteria",
    )
    risk_tolerance: RiskTolerance = Field(
        RiskTolerance.MEDIUM,
        description="How much risk the change is allowed to introduce",
    )
    language: str = Field("python", description="Primary language of the target codebase")
    max_iterations: int = Field(5, ge=1, le=15, description="Max Implementer\u2194Verifier loops per branch")

    def summary(self) -> str:
        criteria = "\n".join(f"- {c}" for c in self.acceptance_criteria) or "- (none provided)"
        return (
            f"Title: {self.title}\n\n"
            f"Description:\n{self.description}\n\n"
            f"Acceptance Criteria:\n{criteria}\n\n"
            f"Risk tolerance: {self.risk_tolerance.value}"
        )
