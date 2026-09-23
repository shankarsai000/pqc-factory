"""Final Production-Qualified Change report."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PQCStatus(str, Enum):
    PRODUCTION_QUALIFIED = "production_qualified"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class PQCReport(BaseModel):
    """Complete output of a successful (or partial) run."""

    status: PQCStatus
    ticket_title: str
    winner_branch_id: Optional[str] = None
    winner_approach: Optional[str] = None
    overall_score: float = 0.0
    risk_score: int = Field(50, ge=0, le=100)

    summary: str = ""
    changes_made: List[str] = Field(default_factory=list)
    test_summary: str = ""
    security_summary: str = ""
    performance_summary: str = ""
    rollback_plan: str = ""
    recommended_next_steps: List[str] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)

    branches_evaluated: int = 0
    scores: Dict[str, float] = Field(default_factory=dict)
    decision_log_path: Optional[str] = None
    pr_ready: bool = False
    raw_metrics: Dict[str, Any] = Field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            "# Production-Qualified Change Report",
            "",
            f"**Status:** `{self.status.value}`",
            f"**Ticket:** {self.ticket_title}",
            f"**Overall Score:** {self.overall_score:.1f}/100",
            f"**Risk Score:** {self.risk_score}/100 (lower is safer)",
            "",
            "## 1. Summary",
            self.summary or "_No summary generated._",
            "",
            "## 2. Changes Made",
        ]
        if self.changes_made:
            lines.extend(f"- {c}" for c in self.changes_made)
        else:
            lines.append("- (none recorded)")

        lines.extend([
            "",
            "## 3. Test Results",
            self.test_summary or "_No test summary._",
            "",
            "## 4. Security Analysis",
            self.security_summary or "_No security summary._",
            "",
            "## 5. Performance Impact",
            self.performance_summary or "_No performance summary._",
            "",
            "## 6. Risk Score Justification",
            f"Risk score of **{self.risk_score}/100**.",
            "",
            "## 7. Rollback Plan",
            self.rollback_plan or "_Revert the pull request / restore previous commit._",
            "",
            "## 8. Recommended Next Steps",
        ])
        if self.recommended_next_steps:
            lines.extend(f"- {s}" for s in self.recommended_next_steps)
        else:
            lines.append("- Review and merge the change.")

        if self.changed_files:
            lines.extend(["", "## Changed Files"])
            lines.extend(f"- `{f}`" for f in self.changed_files)

        return "\n".join(lines)
