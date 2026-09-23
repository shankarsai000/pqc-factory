"""Performance agent."""

from __future__ import annotations

import re

from pqc_factory.agents.base import BaseAgent
from pqc_factory.agents.prompts import PERFORMANCE_SYSTEM
from pqc_factory.models.agent_io import PerformanceResult


class PerformanceAgent(BaseAgent):
    def run(self, sandbox_id: str, changed_files: list[str] | None = None) -> PerformanceResult:
        if self.llm.api_key.startswith("dummy"):
            return PerformanceResult(
                latency_change="neutral",
                memory_change="neutral",
                notes="Local mode – no significant performance regression detected.",
                score=80.0,
            )

        files_info = ""
        if changed_files:
            for f in changed_files:
                content = self.sandbox.read_file(sandbox_id, f)
                files_info += f"\n--- {f} ---\n{content}\n"

        messages = [
            {"role": "system", "content": PERFORMANCE_SYSTEM},
            {"role": "user", "content": f"Analyze performance impact:\n{files_info}"},
        ]
        raw = self.llm.chat(messages, model=self.model)
        return self._parse(raw)

    def _parse(self, raw: str) -> PerformanceResult:
        latency = "neutral"
        memory = "neutral"
        notes = ""
        score = 70.0

        m = re.search(r"latency_change:\s*([^\n]+)", raw, re.I)
        if m:
            latency = m.group(1).strip()
        m = re.search(r"memory_change:\s*([^\n]+)", raw, re.I)
        if m:
            memory = m.group(1).strip()
        m = re.search(r"notes:\s*(.+?)(?=OVERALL|$)", raw, re.S | re.I)
        if m:
            notes = m.group(1).strip()
        m = re.search(r"OVERALL_PERFORMANCE_SCORE:\s*([\d.]+)", raw, re.I)
        if m:
            score = float(m.group(1))

        return PerformanceResult(
            latency_change=latency,
            memory_change=memory,
            notes=notes,
            score=score,
        )
