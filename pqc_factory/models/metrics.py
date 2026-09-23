"""Branch evaluation metrics and scoring."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class BranchMetrics(BaseModel):
    """Metrics collected for a single sandbox branch."""

    branch_id: str
    approach_name: str = ""
    test_pass_rate: float = Field(0.0, ge=0.0, le=1.0)
    coverage: float = Field(0.0, ge=0.0, le=1.0)
    security_score: float = Field(50.0, ge=0.0, le=100.0)
    performance_score: float = Field(50.0, ge=0.0, le=100.0)
    code_quality_score: float = Field(50.0, ge=0.0, le=100.0)
    iterations_used: int = 0
    critical_security_issues: int = 0
    high_security_issues: int = 0
    latency_change_pct: Optional[float] = None
    memory_change_pct: Optional[float] = None
    overall_score: float = Field(0.0, ge=0.0, le=100.0)
    notes: str = ""

    def compute_overall(
        self,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Compute weighted overall score. Higher is better."""
        w = weights or {
            "test": 0.35,
            "security": 0.25,
            "performance": 0.15,
            "quality": 0.15,
            "risk": 0.10,
        }
        risk_penalty = min(100.0, self.critical_security_issues * 40 + self.high_security_issues * 15)
        risk_score = max(0.0, 100.0 - risk_penalty)

        score = (
            w["test"] * (self.test_pass_rate * 100)
            + w["security"] * self.security_score
            + w["performance"] * self.performance_score
            + w["quality"] * self.code_quality_score
            + w["risk"] * risk_score
        )
        self.overall_score = round(score, 2)
        return self.overall_score
