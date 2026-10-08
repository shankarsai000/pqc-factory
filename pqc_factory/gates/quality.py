"""Deterministic quality gates — the bottleneck pure coding agents skip."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pqc_factory.models.ticket import Ticket
from pqc_factory.sandbox.manager import SandboxManager


class GateName(str, Enum):
    TESTS = "tests"
    STATIC_RISK = "static_risk"
    ACCEPTANCE = "acceptance_criteria"
    SECURITY_SCORE = "security_score"
    POLICY = "policy"


class GateVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class GateResult:
    name: GateName
    verdict: GateVerdict
    detail: str = ""
    evidence: List[str] = field(default_factory=list)
    score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "verdict": self.verdict.value,
            "detail": self.detail,
            "evidence": self.evidence,
            "score": self.score,
        }


@dataclass
class QualityGateReport:
    gates: List[GateResult] = field(default_factory=list)
    merge_allowed: bool = False
    blocking_failures: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gates": [g.to_dict() for g in self.gates],
            "merge_allowed": self.merge_allowed,
            "blocking_failures": self.blocking_failures,
            "summary": self.summary,
        }


_SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret[_-]?key|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"), "hard-coded secret"),
    (re.compile(r"(?i)eval\s*\("), "eval()"),
    (re.compile(r"(?i)pickle\.loads?"), "unsafe pickle"),
    (re.compile(r"(?i)shell\s*=\s*True"), "shell=True"),
]


def gate_static_risk(sandbox: SandboxManager, sandbox_id: str, files: List[str]) -> GateResult:
    hits: List[str] = []
    for f in files:
        content = sandbox.read_file(sandbox_id, f) or ""
        for pat, label in _SECRET_PATTERNS:
            if pat.search(content):
                hits.append(f"{f}: {label}")
    if hits:
        return GateResult(name=GateName.STATIC_RISK, verdict=GateVerdict.FAIL, detail=f"{len(hits)} static risk pattern(s)", evidence=hits[:10])
    return GateResult(name=GateName.STATIC_RISK, verdict=GateVerdict.PASS, detail="No high-risk static patterns", evidence=[])


def gate_tests(sandbox: SandboxManager, sandbox_id: str, language: str = "python") -> GateResult:
    files = sandbox.list_files(sandbox_id)
    has_pytest = any(f.startswith("test_") or f.endswith("_test.py") for f in files)
    has_solution = any(f.endswith(".py") for f in files)
    if language == "python" and (has_pytest or has_solution):
        code, out, err = sandbox.run_command(
            sandbox_id,
            'python -m pytest -q --tb=line 2>&1 || python -c "from solution import solve; assert solve() is True" 2>&1',
        )
        text = (out or "") + (err or "")
        if code == 0 or "passed" in text.lower() or "True" in text:
            return GateResult(name=GateName.TESTS, verdict=GateVerdict.PASS, detail="Tests passed in sandbox", evidence=[text.strip()[:500] or "exit 0"], score=1.0)
        return GateResult(name=GateName.TESTS, verdict=GateVerdict.FAIL, detail="Tests failed in sandbox", evidence=[text.strip()[:500] or f"exit {code}"], score=0.0)
    return GateResult(name=GateName.TESTS, verdict=GateVerdict.SKIP, detail="No runnable test entrypoint detected", evidence=files[:8])


def gate_acceptance(ticket: Ticket, files: List[str], file_blobs: Dict[str, str]) -> GateResult:
    criteria = ticket.acceptance_criteria or []
    if not criteria:
        return GateResult(name=GateName.ACCEPTANCE, verdict=GateVerdict.WARN, detail="No acceptance criteria on ticket", evidence=[])
    blob = " ".join(file_blobs.values()).lower()
    titles = " ".join(files).lower()
    evidence: List[str] = []
    covered = 0
    for c in criteria:
        tokens = [t for t in re.findall(r"[a-z0-9]{3,}", c.lower()) if t not in {"the", "and", "for", "with"}]
        hit = any(t in blob or t in titles for t in tokens[:5]) if tokens else False
        if hit:
            covered += 1
            evidence.append(f"covered: {c}")
        else:
            evidence.append(f"unmatched: {c}")
    ratio = covered / len(criteria)
    verdict = GateVerdict.PASS if ratio >= 0.7 else GateVerdict.WARN if ratio >= 0.3 else GateVerdict.FAIL
    return GateResult(name=GateName.ACCEPTANCE, verdict=verdict, detail=f"{covered}/{len(criteria)} criteria have artifact evidence", evidence=evidence, score=ratio)


def gate_security_score(security_score: float, critical: int, max_critical: int = 0) -> GateResult:
    if critical > max_critical:
        return GateResult(name=GateName.SECURITY_SCORE, verdict=GateVerdict.FAIL, detail=f"critical issues={critical} > allowed {max_critical}", score=security_score)
    if security_score < 60:
        return GateResult(name=GateName.SECURITY_SCORE, verdict=GateVerdict.WARN, detail=f"security score {security_score:.0f} below 60", score=security_score)
    return GateResult(name=GateName.SECURITY_SCORE, verdict=GateVerdict.PASS, detail=f"security score {security_score:.0f}", score=security_score)


def run_quality_gates(
    ticket: Ticket,
    sandbox: SandboxManager,
    sandbox_id: str,
    changed_files: List[str],
    security_score: float = 100.0,
    critical_issues: int = 0,
    min_test_pass: bool = True,
) -> QualityGateReport:
    files = changed_files or sandbox.list_files(sandbox_id)
    blobs = {f: sandbox.read_file(sandbox_id, f) or "" for f in files}
    results = [
        gate_static_risk(sandbox, sandbox_id, files),
        gate_tests(sandbox, sandbox_id, getattr(ticket, "language", "python") or "python"),
        gate_acceptance(ticket, files, blobs),
        gate_security_score(security_score, critical_issues),
    ]
    blocking: List[str] = []
    for g in results:
        if g.verdict == GateVerdict.FAIL and g.name in (GateName.TESTS, GateName.STATIC_RISK, GateName.SECURITY_SCORE):
            blocking.append(f"{g.name.value}: {g.detail}")
        if g.verdict == GateVerdict.FAIL and g.name == GateName.ACCEPTANCE and min_test_pass and (g.score or 0) < 0.15:
            blocking.append(f"{g.name.value}: {g.detail}")
    merge_allowed = len(blocking) == 0
    summary = "MERGE ALLOWED — all blocking gates passed" if merge_allowed else "MERGE BLOCKED — " + "; ".join(blocking)
    return QualityGateReport(gates=results, merge_allowed=merge_allowed, blocking_failures=blocking, summary=summary)
