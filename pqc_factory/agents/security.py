"""Security agent."""

from __future__ import annotations

import re

from pqc_factory.agents.base import BaseAgent
from pqc_factory.agents.prompts import SECURITY_SYSTEM
from pqc_factory.models.agent_io import SecurityResult


class SecurityAgent(BaseAgent):
    def run(self, sandbox_id: str, changed_files: list[str] | None = None) -> SecurityResult:
        files_info = ""
        if changed_files:
            for f in changed_files:
                content = self.sandbox.read_file(sandbox_id, f)
                files_info += f"\n--- {f} ---\n{content}\n"

        user_content = f"Analyze the following code for security issues:\n{files_info or '(no files)'}"

        messages = [
            {"role": "system", "content": SECURITY_SYSTEM},
            {"role": "user", "content": user_content},
        ]

        if self.llm.api_key.startswith("dummy"):
            return SecurityResult(
                critical=0,
                high=0,
                medium=0,
                low=1,
                findings=["[LOW] No obvious secrets or injection points (local mode)"],
                recommendations=["Add input validation when handling external data"],
                score=92.0,
            )

        raw = self.llm.chat(messages, model=self.model)
        return self._parse(raw)

    def _parse(self, raw: str) -> SecurityResult:
        def _num(pattern: str) -> int:
            m = re.search(pattern, raw, re.I)
            return int(m.group(1)) if m else 0

        critical = _num(r"critical:\s*(\d+)")
        high = _num(r"high:\s*(\d+)")
        medium = _num(r"medium:\s*(\d+)")
        low = _num(r"low:\s*(\d+)")

        score = 100.0
        score -= critical * 40 + high * 15 + medium * 5 + low * 1
        score = max(0.0, min(100.0, score))

        m = re.search(r"OVERALL_SECURITY_SCORE:\s*([\d.]+)", raw, re.I)
        if m:
            score = float(m.group(1))

        return SecurityResult(
            critical=critical,
            high=high,
            medium=medium,
            low=low,
            findings=[],
            recommendations=[],
            score=score,
        )
