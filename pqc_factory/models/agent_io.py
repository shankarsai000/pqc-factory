"""Shared input/output schemas for specialist agents."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Generic request passed to any specialist agent."""

    task: str
    context: str = ""
    sandbox_id: str
    branch_id: str
    extra: Dict[str, Any] = Field(default_factory=dict)


class ImplementerResult(BaseModel):
    thought: str = ""
    changed_files: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    success: bool = True
    message: str = ""


class VerifierResult(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    failures: List[str] = Field(default_factory=list)
    feedback: str = ""
    overall: str = "FAIL"  # PASS | FAIL
    coverage: float = 0.0


class SecurityResult(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    score: float = 50.0


class PerformanceResult(BaseModel):
    latency_change: str = "neutral"
    memory_change: str = "neutral"
    notes: str = ""
    score: float = 50.0


class DocumentationResult(BaseModel):
    markdown_report: str = ""
    risk_score: int = 50
    rollback_plan: str = ""
    summary: str = ""
