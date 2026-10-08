"""Baseline delta metrics — before vs after measurements for a PQC run."""

from __future__ import annotations

import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from pqc_factory.sandbox.manager import SandboxManager


class DeltaVerdict(str, Enum):
    IMPROVED = "improved"
    NO_REGRESSION = "no_regression"
    REGRESSION = "regression"
    INCONCLUSIVE = "inconclusive"


class Snapshot(BaseModel):
    label: str = "baseline"
    test_pass_rate: float = 0.0
    tests_passed: int = 0
    tests_total: int = 0
    security_score: float = 100.0
    critical_issues: int = 0
    high_issues: int = 0
    static_risk_hits: int = 0
    file_count: int = 0
    probe_ms: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BaselineDelta(BaseModel):
    before: Snapshot
    after: Snapshot
    test_delta: float = 0.0
    security_delta: float = 0.0
    critical_delta: int = 0
    probe_ms_delta: Optional[float] = None
    verdict: DeltaVerdict = DeltaVerdict.INCONCLUSIVE
    summary_lines: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    def to_markdown_section(self) -> str:
        lines = [
            "## Baseline Delta (before → after)",
            "",
            f"**Verdict:** `{self.verdict.value}`",
            "",
            "| Metric | Before | After | Δ |",
            "|--------|--------|-------|---|",
            f"| Tests pass rate | {self.before.test_pass_rate:.0%} | {self.after.test_pass_rate:.0%} | {self.test_delta:+.0%} |",
            f"| Tests (passed/total) | {self.before.tests_passed}/{self.before.tests_total} | {self.after.tests_passed}/{self.after.tests_total} | — |",
            f"| Security score | {self.before.security_score:.0f} | {self.after.security_score:.0f} | {self.security_delta:+.0f} |",
            f"| Critical issues | {self.before.critical_issues} | {self.after.critical_issues} | {self.critical_delta:+d} |",
            f"| Static risk hits | {self.before.static_risk_hits} | {self.after.static_risk_hits} | {self.after.static_risk_hits - self.before.static_risk_hits:+d} |",
        ]
        if self.probe_ms_delta is not None and self.before.probe_ms is not None:
            lines.append(
                f"| Probe latency (ms) | {self.before.probe_ms:.1f} | {self.after.probe_ms or 0:.1f} | {self.probe_ms_delta:+.1f} |"
            )
        lines.append("")
        for s in self.summary_lines:
            lines.append(f"- {s}")
        return "\n".join(lines)


def _run_tests(sandbox: SandboxManager, sandbox_id: str):
    code, out, err = sandbox.run_command(
        sandbox_id,
        'python -m pytest -q --tb=line 2>&1 || python -c "from solution import solve; assert solve() is True; print(\'1 passed\')" 2>&1',
    )
    text = ((out or "") + (err or "")).strip()
    passed = total = 0
    m = re.search(r"(\d+)\s+passed", text)
    if m:
        passed = int(m.group(1))
        total = passed
    m2 = re.search(r"(\d+)\s+failed", text)
    if m2:
        total = max(total, passed + int(m2.group(1)))
    if code == 0 and total == 0 and ("True" in text or "passed" in text.lower()):
        passed, total = 1, 1
    if total == 0 and code != 0:
        return 0, 1, 0.0, text[:300]
    rate = (passed / total) if total else (1.0 if code == 0 else 0.0)
    if total == 0 and code == 0:
        passed, total, rate = 0, 0, 0.0
    return passed, total, rate, text[:300]


def _static_hits(sandbox: SandboxManager, sandbox_id: str) -> int:
    pats = [
        re.compile(r"(?i)(api[_-]?key|secret[_-]?key|password)\s*=\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"(?i)eval\s*\("),
        re.compile(r"(?i)pickle\.loads?"),
        re.compile(r"(?i)shell\s*=\s*True"),
    ]
    hits = 0
    for f in sandbox.list_files(sandbox_id):
        if not f.endswith((".py", ".js", ".ts", ".go")):
            continue
        content = sandbox.read_file(sandbox_id, f) or ""
        for p in pats:
            if p.search(content):
                hits += 1
    return hits


def _probe_ms(sandbox: SandboxManager, sandbox_id: str) -> Optional[float]:
    t0 = time.perf_counter()
    code, _, _ = sandbox.run_command(
        sandbox_id,
        'python -c "try:\n from solution import solve; solve()\nexcept Exception:\n pass" 2>&1',
    )
    return round((time.perf_counter() - t0) * 1000, 2)


def capture_snapshot(
    sandbox: SandboxManager,
    sandbox_id: str,
    label: str = "baseline",
    security_score: float = 100.0,
    critical: int = 0,
    high: int = 0,
) -> Snapshot:
    passed, total, rate, note = _run_tests(sandbox, sandbox_id)
    hits = _static_hits(sandbox, sandbox_id)
    probe = _probe_ms(sandbox, sandbox_id)
    return Snapshot(
        label=label,
        test_pass_rate=rate,
        tests_passed=passed,
        tests_total=total,
        security_score=security_score,
        critical_issues=critical,
        high_issues=high,
        static_risk_hits=hits,
        file_count=len(sandbox.list_files(sandbox_id)),
        probe_ms=probe,
        notes=note,
    )


def compute_delta(before: Snapshot, after: Snapshot) -> BaselineDelta:
    test_delta = after.test_pass_rate - before.test_pass_rate
    security_delta = after.security_score - before.security_score
    critical_delta = after.critical_issues - before.critical_issues
    probe_delta = None
    if before.probe_ms is not None and after.probe_ms is not None:
        probe_delta = after.probe_ms - before.probe_ms
    lines: List[str] = []
    regression = False
    improved = False
    if before.tests_total > 0 and after.test_pass_rate < before.test_pass_rate - 1e-9:
        regression = True
        lines.append(f"Test pass rate regressed ({before.test_pass_rate:.0%} → {after.test_pass_rate:.0%})")
    elif after.test_pass_rate > before.test_pass_rate + 1e-9:
        improved = True
        lines.append(f"Test pass rate improved ({before.test_pass_rate:.0%} → {after.test_pass_rate:.0%})")
    elif after.tests_total > before.tests_total:
        improved = True
        lines.append(f"More tests present ({before.tests_total} → {after.tests_total})")
    else:
        lines.append("Tests: no regression")
    if critical_delta > 0:
        regression = True
        lines.append(f"Critical security issues increased by {critical_delta}")
    elif after.static_risk_hits > before.static_risk_hits:
        regression = True
        lines.append("Static risk patterns increased")
    else:
        lines.append("Security: no new critical/static risk")
    if probe_delta is not None and probe_delta > 50:
        lines.append(f"Probe latency increased by {probe_delta:.0f}ms (warn)")
    elif probe_delta is not None and probe_delta < -5:
        improved = True
        lines.append(f"Probe latency improved by {-probe_delta:.0f}ms")
    if regression:
        verdict = DeltaVerdict.REGRESSION
    elif improved:
        verdict = DeltaVerdict.IMPROVED
    elif before.tests_total == 0 and after.tests_total == 0:
        verdict = DeltaVerdict.INCONCLUSIVE
    else:
        verdict = DeltaVerdict.NO_REGRESSION
    return BaselineDelta(
        before=before,
        after=after,
        test_delta=test_delta,
        security_delta=security_delta,
        critical_delta=critical_delta,
        probe_ms_delta=probe_delta,
        verdict=verdict,
        summary_lines=lines,
    )
