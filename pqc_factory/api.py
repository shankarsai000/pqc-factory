"""FastAPI server for PQC Factory — deployable on Nebius Serverless Endpoints."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pqc_factory.models.ticket import Ticket
from pqc_factory.models.pqc_report import PQCReport

app = FastAPI(
    title="PQC Factory API",
    description="Production-Qualified Change Factory — multi-agent coding on Nebius Token Factory + Nemotron",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_JOBS: Dict[str, Dict[str, Any]] = {}


class RunRequest(BaseModel):
    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=20)
    acceptance_criteria: List[str] = Field(default_factory=list)
    language: str = "python"
    risk_tolerance: str = "medium"
    max_branches: int = Field(2, ge=1, le=4)
    max_iterations: int = Field(3, ge=1, le=10)
    async_mode: bool = False


class RunResponse(BaseModel):
    job_id: str
    status: str
    message: str = ""
    report: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    sandbox_mode: str
    nebius_configured: bool
    tavily_configured: bool
    time: str


def _env_configured(name: str) -> bool:
    v = os.getenv(name, "")
    return bool(v) and not v.startswith("dummy") and "your_" not in v.lower()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.2.0",
        sandbox_mode=os.getenv("SANDBOX_MODE", "local"),
        nebius_configured=_env_configured("NEBIUS_API_KEY"),
        tavily_configured=_env_configured("TAVILY_API_KEY"),
        time=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/")
def root() -> Dict[str, str]:
    return {"service": "PQC Factory", "docs": "/docs", "health": "/health", "run": "POST /v1/run"}


def _execute_run(job_id: str, ticket: Ticket, max_branches: int, max_iterations: int) -> None:
    _JOBS[job_id]["status"] = "running"
    try:
        from pqc_factory.orchestrator.engine import PQCEngine
        engine = PQCEngine(max_branches=max_branches, max_iterations=max_iterations)
        report: PQCReport = engine.run(ticket)
        _JOBS[job_id]["status"] = "completed"
        _JOBS[job_id]["report"] = report.model_dump(mode="json")
        _JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = str(e)
        _JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


@app.post("/v1/run", response_model=RunResponse)
def run_pqc(body: RunRequest, background_tasks: BackgroundTasks) -> RunResponse:
    try:
        ticket = Ticket(
            title=body.title,
            description=body.description,
            acceptance_criteria=body.acceptance_criteria,
            language=body.language,
            risk_tolerance=body.risk_tolerance,  # type: ignore[arg-type]
            max_iterations=body.max_iterations,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "ticket_title": ticket.title,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "report": None,
        "error": None,
    }

    if body.async_mode:
        background_tasks.add_task(_execute_run, job_id, ticket, body.max_branches, body.max_iterations)
        return RunResponse(job_id=job_id, status="queued", message="Job queued. Poll GET /v1/jobs/{job_id}")

    _execute_run(job_id, ticket, body.max_branches, body.max_iterations)
    job = _JOBS[job_id]
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=job.get("error") or "run failed")
    return RunResponse(job_id=job_id, status=job["status"], report=job.get("report"), message="PQC run completed")


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/v1/jobs")
def list_jobs() -> Dict[str, Any]:
    return {"jobs": list(_JOBS.values()), "count": len(_JOBS)}


def create_app() -> FastAPI:
    return app
