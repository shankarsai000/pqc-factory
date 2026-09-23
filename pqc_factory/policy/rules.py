"""Policy packs - YAML-driven gates for production qualification."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from pqc_factory.models.metrics import BranchMetrics
from pqc_factory.models.pqc_report import PQCReport, PQCStatus


class PolicyRules(BaseModel):
    max_risk_score: int = Field(60, description="Fail if risk above this")
    min_overall_score: float = Field(70.0, description="Min overall to be PQ")
    max_critical_security: int = Field(0, description="Critical findings allowed")
    max_high_security: int = Field(2, description="High findings allowed")
    min_test_pass_rate: float = Field(0.8, ge=0.0, le=1.0)
    block_new_deps: bool = False
    require_pr_ready: bool = True

    def evaluate(self, metrics: BranchMetrics) -> List[str]:
        violations: List[str] = []
        if metrics.critical_security_issues > self.max_critical_security:
            violations.append(
                f"critical_security={metrics.critical_security_issues} > {self.max_critical_security}"
            )
        if metrics.high_security_issues > self.max_high_security:
            violations.append(
                f"high_security={metrics.high_security_issues} > {self.max_high_security}"
            )
        if metrics.test_pass_rate < self.min_test_pass_rate:
            violations.append(
                f"test_pass_rate={metrics.test_pass_rate:.2f} < {self.min_test_pass_rate}"
            )
        if metrics.overall_score < self.min_overall_score:
            violations.append(
                f"overall_score={metrics.overall_score:.1f} < {self.min_overall_score}"
            )
        return violations

    def apply_to_report(self, report: PQCReport, winner: Optional[BranchMetrics] = None) -> PQCReport:
        violations: List[str] = []
        if report.risk_score > self.max_risk_score:
            violations.append(f"risk_score={report.risk_score} > {self.max_risk_score}")
        if winner:
            violations.extend(self.evaluate(winner))
        if violations:
            report.status = PQCStatus.NEEDS_REVIEW
            report.pr_ready = False
            extra = "Policy violations: " + "; ".join(violations)
            report.summary = (report.summary or "") + f"\n\n{extra}"
            report.recommended_next_steps = list(report.recommended_next_steps) + [
                f"Resolve: {v}" for v in violations
            ]
        return report


def load_policy(path: Optional[str | Path] = None) -> PolicyRules:
    if path is None:
        return PolicyRules()
    p = Path(path)
    if not p.exists():
        return PolicyRules()
    text = p.read_text(encoding="utf-8")
    data: Dict[str, Any]
    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(text) or {}
        except ImportError:
            data = {}
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                if v.lower() in ("true", "false"):
                    data[k] = v.lower() == "true"
                else:
                    try:
                        data[k] = float(v) if "." in v else int(v)
                    except ValueError:
                        data[k] = v
    else:
        import json
        data = json.loads(text)
    return PolicyRules(**{k: v for k, v in data.items() if k in PolicyRules.model_fields})
