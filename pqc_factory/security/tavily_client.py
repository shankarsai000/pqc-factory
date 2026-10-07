"""Tavily-backed CVE / advisory lookup for the Security agent (hackathon bonus path)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import httpx


@dataclass
class CVEFinding:
    title: str
    url: str = ""
    snippet: str = ""
    severity_hint: str = "medium"
    source: str = "tavily"


@dataclass
class TavilySecurityReport:
    query: str
    findings: List[CVEFinding] = field(default_factory=list)
    raw_answer: str = ""
    enabled: bool = False
    error: Optional[str] = None

    def as_findings_lines(self) -> List[str]:
        lines: List[str] = []
        for f in self.findings:
            tag = f.severity_hint.upper()
            lines.append(f"[{tag}] {f.title}" + (f" — {f.url}" if f.url else ""))
        if self.raw_answer and not lines:
            lines.append(f"[INFO] Tavily: {self.raw_answer[:300]}")
        return lines


def _severity_from_text(text: str) -> str:
    t = text.lower()
    if "critical" in t or "rce" in t or "remote code" in t:
        return "critical"
    if "high" in t or "sql injection" in t or "auth bypass" in t:
        return "high"
    if "low" in t or "info" in t:
        return "low"
    return "medium"


class TavilyClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.timeout = timeout
        self.base_url = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("dummy")

    def search_cves(
        self,
        libraries: Optional[List[str]] = None,
        code_hints: str = "",
        max_results: int = 5,
    ) -> TavilySecurityReport:
        libs = [x.strip() for x in (libraries or []) if x and x.strip()]
        if not libs and code_hints:
            libs = list(
                dict.fromkeys(
                    re.findall(
                        r"(?:import|from|require\(|from\s+['\"])\s*([a-zA-Z0-9_\-./]+)",
                        code_hints,
                    )
                )
            )[:8]
        query_parts = ["CVE security vulnerability advisory"]
        if libs:
            query_parts.append(" ".join(libs[:5]))
        if code_hints:
            query_parts.append(code_hints[:200])
        query = " ".join(query_parts)
        if not self.enabled:
            return TavilySecurityReport(query=query, enabled=False, error="TAVILY_API_KEY not set")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url.rstrip('/')}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": True,
                        "max_results": max_results,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return TavilySecurityReport(query=query, enabled=True, error=str(e))
        findings: List[CVEFinding] = []
        for item in data.get("results") or []:
            title = item.get("title") or item.get("url") or "result"
            content = item.get("content") or item.get("snippet") or ""
            findings.append(
                CVEFinding(
                    title=title,
                    url=item.get("url") or "",
                    snippet=content[:400],
                    severity_hint=_severity_from_text(f"{title} {content}"),
                )
            )
        return TavilySecurityReport(
            query=query,
            findings=findings,
            raw_answer=str(data.get("answer") or ""),
            enabled=True,
        )
