"""Security agent — static heuristics + optional Tavily CVE feeds."""

from __future__ import annotations

import re
from typing import List, Optional

from pqc_factory.agents.base import BaseAgent
from pqc_factory.agents.prompts import SECURITY_SYSTEM
from pqc_factory.models.agent_io import SecurityResult
from pqc_factory.security.tavily_client import TavilyClient


class SecurityAgent(BaseAgent):
    def __init__(self, llm, sandbox, model=None, tavily: Optional[TavilyClient] = None):
        super().__init__(llm, sandbox, model)
        self.tavily = tavily or TavilyClient()

    def run(self, sandbox_id: str, changed_files: list[str] | None = None) -> SecurityResult:
        files_info = ""
        blob = ""
        if changed_files:
            for f in changed_files:
                content = self.sandbox.read_file(sandbox_id, f)
                files_info += f"\n--- {f} ---\n{content}\n"
                blob += content + "\n"

        if self.llm.api_key.startswith("dummy"):
            return self._local_scan(blob, files_info)

        user_content = f"Analyze the following code for security issues:\n{files_info or '(no files)'}"
        tavily_report = self.tavily.search_cves(code_hints=blob[:1500])
        if tavily_report.enabled and tavily_report.findings:
            user_content += "\n\nRecent advisory context (Tavily):\n"
            user_content += "\n".join(tavily_report.as_findings_lines()[:8])

        messages = [
            {"role": "system", "content": SECURITY_SYSTEM},
            {"role": "user", "content": user_content},
        ]
        raw = self.llm.chat(messages, model=self.model)
        result = self._parse(raw)
        for line in tavily_report.as_findings_lines()[:5]:
            if line not in result.findings:
                result.findings.append(line)
        return result

    def _local_scan(self, blob: str, files_info: str) -> SecurityResult:
        critical = high = medium = low = 0
        findings: List[str] = []
        patterns = [
            (r"(?i)(api[_-]?key|secret[_-]?key|password)\s*=\s*['\"][^'\"]+['\"]", "high", "Possible hard-coded secret"),
            (r"(?i)eval\s*\(", "high", "Use of eval()"),
            (r"(?i)exec\s*\(", "medium", "Use of exec()"),
            (r"(?i)pickle\.loads?", "high", "Unsafe pickle deserialization"),
            (r"(?i)subprocess\.(call|run|Popen).*shell\s*=\s*True", "high", "shell=True subprocess"),
        ]
        for pat, sev, msg in patterns:
            if re.search(pat, blob):
                findings.append(f"[{sev.upper()}] {msg}")
                if sev == "high":
                    high += 1
                elif sev == "medium":
                    medium += 1
                else:
                    low += 1
        tavily_report = self.tavily.search_cves(code_hints=blob[:1500] or "python security")
        for line in tavily_report.as_findings_lines()[:5]:
            findings.append(line)
            if "[CRITICAL]" in line:
                critical += 1
            elif "[HIGH]" in line:
                high += 1
            elif "[LOW]" in line:
                low += 1
            else:
                medium += 1
        if not findings:
            findings = ["[LOW] No obvious secrets or injection points (local mode)"]
            low = 1
        score = max(0.0, min(100.0, 100.0 - critical * 40 - high * 15 - medium * 5 - low * 1))
        return SecurityResult(
            critical=critical, high=high, medium=medium, low=low,
            findings=findings,
            recommendations=["Add input validation", "Rotate any exposed secrets", "Pin dependencies"],
            score=score,
        )

    def _parse(self, raw: str) -> SecurityResult:
        def _num(pattern: str) -> int:
            m = re.search(pattern, raw, re.I)
            return int(m.group(1)) if m else 0
        critical, high, medium, low = _num(r"critical:\s*(\d+)"), _num(r"high:\s*(\d+)"), _num(r"medium:\s*(\d+)"), _num(r"low:\s*(\d+)")
        score = max(0.0, min(100.0, 100.0 - critical * 40 - high * 15 - medium * 5 - low * 1))
        m = re.search(r"OVERALL_SECURITY_SCORE:\s*([\d.]+)", raw, re.I)
        if m:
            score = float(m.group(1))
        return SecurityResult(critical=critical, high=high, medium=medium, low=low, findings=[], recommendations=[], score=score)
