"""Human-in-the-loop gates - pause, approve, reject with feedback."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional


class GateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_PASS = "auto_pass"


@dataclass
class GateDecision:
    run_id: str
    ticket_title: str
    status: str = GateStatus.PENDING.value
    risk_score: int = 50
    overall_score: float = 0.0
    reason: str = ""
    feedback: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: Optional[str] = None
    report_path: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GateDecision":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class HITLStore:
    def __init__(self, root: Optional[str | Path] = None):
        self.root = Path(root or "./logs/hitl")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def create(
        self,
        ticket_title: str,
        risk_score: int,
        overall_score: float,
        report_path: Optional[str] = None,
        risk_threshold: int = 40,
    ) -> GateDecision:
        run_id = uuid.uuid4().hex[:12]
        if risk_score <= risk_threshold:
            status = GateStatus.AUTO_PASS.value
            decided = datetime.now(timezone.utc).isoformat()
        else:
            status = GateStatus.PENDING.value
            decided = None
        gate = GateDecision(
            run_id=run_id,
            ticket_title=ticket_title,
            status=status,
            risk_score=risk_score,
            overall_score=overall_score,
            decided_at=decided,
            report_path=report_path,
            reason="auto-pass: risk under threshold" if status == GateStatus.AUTO_PASS.value else "",
        )
        self._path(run_id).write_text(json.dumps(gate.to_dict(), indent=2), encoding="utf-8")
        return gate

    def get(self, run_id: str) -> Optional[GateDecision]:
        p = self._path(run_id)
        if not p.exists():
            return None
        return GateDecision.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def approve(self, run_id: str, reason: str = "approved by human") -> GateDecision:
        gate = self.get(run_id)
        if not gate:
            raise KeyError(f"Unknown run_id: {run_id}")
        gate.status = GateStatus.APPROVED.value
        gate.reason = reason
        gate.decided_at = datetime.now(timezone.utc).isoformat()
        self._path(run_id).write_text(json.dumps(gate.to_dict(), indent=2), encoding="utf-8")
        return gate

    def reject(self, run_id: str, reason: str, feedback: str = "") -> GateDecision:
        gate = self.get(run_id)
        if not gate:
            raise KeyError(f"Unknown run_id: {run_id}")
        gate.status = GateStatus.REJECTED.value
        gate.reason = reason
        gate.feedback = feedback or reason
        gate.decided_at = datetime.now(timezone.utc).isoformat()
        self._path(run_id).write_text(json.dumps(gate.to_dict(), indent=2), encoding="utf-8")
        return gate

    def list_pending(self) -> List[GateDecision]:
        out: List[GateDecision] = []
        for p in sorted(self.root.glob("*.json")):
            try:
                g = GateDecision.from_dict(json.loads(p.read_text(encoding="utf-8")))
                if g.status == GateStatus.PENDING.value:
                    out.append(g)
            except Exception:
                continue
        return out

    def feedback_for_implementer(self, run_id: str) -> str:
        gate = self.get(run_id)
        if not gate or gate.status != GateStatus.REJECTED.value:
            return ""
        return (
            f"Human reviewer rejected this change.\n"
            f"Reason: {gate.reason}\n"
            f"Feedback: {gate.feedback}\n"
            f"Please address the feedback and improve the implementation."
        )
