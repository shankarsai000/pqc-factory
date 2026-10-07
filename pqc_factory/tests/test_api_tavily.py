"""Tests for Tavily client (offline) and FastAPI health/run."""

from fastapi.testclient import TestClient

from pqc_factory.security.tavily_client import TavilyClient
from pqc_factory.api import app
from pqc_factory.agents.security import SecurityAgent
from pqc_factory.llm.client import LLMClient
from pqc_factory.sandbox.manager import SandboxManager


def test_tavily_disabled_without_key():
    client = TavilyClient(api_key="dummy")
    assert not client.enabled
    report = client.search_cves(libraries=["requests"])
    assert report.enabled is False
    assert report.error


def test_security_local_heuristics():
    llm = LLMClient(api_key="dummy")
    sb = SandboxManager(mode="local")
    agent = SecurityAgent(llm, sb, tavily=TavilyClient(api_key="dummy"))
    base = sb.create_base("sec")
    sb.write_file(base, "bad.py", 'password = "supersecret"\neval("1")\n')
    result = agent.run(base, ["bad.py"])
    assert result.score < 100
    assert result.findings
    sb.cleanup()


def test_api_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_run_sync():
    client = TestClient(app)
    r = client.post(
        "/v1/run",
        json={
            "title": "Add a small helper function",
            "description": "Create a utility that returns True for the demo pipeline path.",
            "acceptance_criteria": ["works"],
            "max_branches": 1,
            "max_iterations": 2,
            "async_mode": False,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "completed"
    assert data["report"] is not None
