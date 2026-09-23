"""Tier 2: memory, HITL, language routing."""

from pathlib import Path

from pqc_factory.memory.store import MemoryStore, RunOutcome
from pqc_factory.hitl.gates import HITLStore, GateStatus
from pqc_factory.agents.language import detect_language, route_specialists
from pqc_factory.models.ticket import Ticket
from pqc_factory.orchestrator.planner import plan_approaches


def test_memory_preferred_approaches(tmp_path: Path):
    store = MemoryStore(tmp_path / "mem.jsonl")
    store.record(
        RunOutcome(
            ticket_title="Add rate limiter",
            language="python",
            winner_approach="defensive-robust",
            overall_score=90,
            risk_score=20,
            status="production_qualified",
            approaches_tried=["minimal-direct", "defensive-robust"],
            keywords=["rate", "limiter", "add"],
        )
    )
    preferred = store.preferred_approaches(
        "Add rate limiter helper", "Need a rate limiter for API",
        language="python", max_branches=2,
    )
    assert preferred[0] == "defensive-robust"


def test_hitl_auto_pass_and_reject(tmp_path: Path):
    hitl = HITLStore(tmp_path / "hitl")
    g = hitl.create("low risk change", risk_score=10, overall_score=90, risk_threshold=40)
    assert g.status == GateStatus.AUTO_PASS.value
    g2 = hitl.create("risky", risk_score=80, overall_score=70, risk_threshold=40)
    assert g2.status == GateStatus.PENDING.value
    rejected = hitl.reject(g2.run_id, reason="too risky", feedback="add more tests")
    assert rejected.status == GateStatus.REJECTED.value
    assert "add more tests" in hitl.feedback_for_implementer(g2.run_id)


def test_language_detection():
    assert detect_language("typescript") == "typescript"
    assert detect_language(text="rewrite the go service") == "go"
    assert detect_language(filenames=["src/main.rs"]) == "rust"
    impl, ver, cmd = route_specialists("go")
    assert "Go" in impl
    assert "go test" in cmd


def test_planner_uses_memory(tmp_path: Path):
    store = MemoryStore(tmp_path / "mem2.jsonl")
    store.record(
        RunOutcome(
            ticket_title="Clean API design",
            language="python",
            winner_approach="clean-architecture",
            overall_score=88,
            risk_score=15,
            status="production_qualified",
            approaches_tried=["clean-architecture"],
            keywords=["clean", "api", "design"],
        )
    )
    ticket = Ticket(
        title="Clean API design helpers",
        description="Refactor helpers toward a clean architecture style for the service layer.",
        language="python",
    )
    approaches = plan_approaches(ticket, max_branches=2, memory=store)
    assert "clean-architecture" in approaches
