"""Learning memory - store past PQC outcomes and bias the planner."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class RunOutcome:
    ticket_title: str
    language: str
    winner_approach: str
    overall_score: float
    risk_score: int
    status: str
    approaches_tried: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RunOutcome":
        return cls(
            ticket_title=d.get("ticket_title", ""),
            language=d.get("language", "python"),
            winner_approach=d.get("winner_approach", ""),
            overall_score=float(d.get("overall_score", 0)),
            risk_score=int(d.get("risk_score", 50)),
            status=d.get("status", ""),
            approaches_tried=list(d.get("approaches_tried") or []),
            keywords=list(d.get("keywords") or []),
            ts=d.get("ts", ""),
        )


def _keywords(text: str) -> List[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with",
        "is", "be", "as", "by", "from", "that", "this", "it", "are",
    }
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in stop][:20]


class MemoryStore:
    def __init__(self, path: Optional[str | Path] = None):
        self.path = Path(path or "./logs/pqc_memory.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, outcome: RunOutcome) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(outcome.to_dict()) + "\n")

    def load_all(self) -> List[RunOutcome]:
        if not self.path.exists():
            return []
        out: List[RunOutcome] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(RunOutcome.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return out

    def similar(self, title: str, description: str, language: str, limit: int = 10) -> List[RunOutcome]:
        keys = set(_keywords(f"{title} {description}"))
        scored = []
        for o in self.load_all():
            lang_bonus = 1.0 if (not o.language or not language or o.language.lower() == language.lower()) else 0.0
            overlap = len(keys & set(o.keywords)) + lang_bonus
            if overlap > 0:
                scored.append((overlap + o.overall_score / 100.0, o))
        scored.sort(key=lambda x: -x[0])
        return [o for _, o in scored[:limit]]

    def preferred_approaches(
        self,
        title: str,
        description: str,
        language: str = "python",
        default: Optional[List[str]] = None,
        max_branches: int = 3,
    ) -> List[str]:
        default = default or ["minimal-direct", "defensive-robust", "clean-architecture"]
        similar = self.similar(title, description, language, limit=15)
        if not similar:
            return default[:max_branches]
        counter: Counter = Counter()
        for o in similar:
            if o.overall_score >= 60 and o.winner_approach:
                counter[o.winner_approach] += 1 + int(o.overall_score // 25)
            for a in o.approaches_tried:
                counter[a] += 1
        ranked = [name for name, _ in counter.most_common()]
        seen, result = set(), []
        for name in ranked + default:
            if name not in seen:
                seen.add(name)
                result.append(name)
            if len(result) >= max_branches:
                break
        return result[:max_branches]


def record_from_report(store: MemoryStore, ticket_title: str, language: str, report, approaches=None) -> RunOutcome:
    outcome = RunOutcome(
        ticket_title=ticket_title,
        language=language,
        winner_approach=getattr(report, "winner_approach", "") or "",
        overall_score=float(getattr(report, "overall_score", 0) or 0),
        risk_score=int(getattr(report, "risk_score", 50) or 50),
        status=getattr(getattr(report, "status", None), "value", str(getattr(report, "status", ""))),
        approaches_tried=list(approaches or []),
        keywords=_keywords(ticket_title),
    )
    store.record(outcome)
    return outcome
