"""Decision / audit logger (JSONL)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class DecisionLogger:
    def __init__(self, path: str | Path = "/tmp/pqc_logs/decisions.jsonl"):
        self.path = Path(path)
        self._records: list[dict] = []
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.path = Path("/tmp/pqc_decisions.jsonl")

    def log(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": data or {},
        }
        self._records.append(record)
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass

    def read_all(self) -> list[dict]:
        if self._records:
            return list(self._records)
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text(encoding="utf-8").strip().splitlines()
            return [json.loads(line) for line in lines if line.strip()]
        except OSError:
            return list(self._records)
