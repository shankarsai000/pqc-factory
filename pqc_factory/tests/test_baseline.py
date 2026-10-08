"""Baseline delta metrics."""

from pqc_factory.eval.baseline import (
    capture_snapshot,
    compute_delta,
    DeltaVerdict,
    Snapshot,
)
from pqc_factory.sandbox.manager import SandboxManager
from pqc_factory.models.ticket import Ticket
from pqc_factory.orchestrator.engine import PQCEngine


def test_compute_delta_regression():
    before = Snapshot(label="b", test_pass_rate=1.0, tests_passed=2, tests_total=2, security_score=90)
    after = Snapshot(label="a", test_pass_rate=0.5, tests_passed=1, tests_total=2, security_score=90, critical_issues=1)
    d = compute_delta(before, after)
    assert d.verdict == DeltaVerdict.REGRESSION
    assert d.critical_delta == 1


def test_compute_delta_improved():
    before = Snapshot(label="b", test_pass_rate=0.0, tests_passed=0, tests_total=0)
    after = Snapshot(label="a", test_pass_rate=1.0, tests_passed=2, tests_total=2, security_score=95)
    d = compute_delta(before, after)
    assert d.verdict in (DeltaVerdict.IMPROVED, DeltaVerdict.NO_REGRESSION)


def test_capture_and_delta_on_sandbox():
    sb = SandboxManager(mode="local")
    base = sb.create_base("base")
    before = capture_snapshot(sb, base, label="before")
    sb.write_file(base, "solution.py", "def solve():\n    return True\n")
    sb.write_file(
        base,
        "test_solution.py",
        "from solution import solve\n\ndef test_ok():\n    assert solve() is True\n",
    )
    after = capture_snapshot(sb, base, label="after")
    d = compute_delta(before, after)
    assert d.verdict in list(DeltaVerdict)
    assert "Baseline Delta" in d.to_markdown_section()
    sb.cleanup()


def test_engine_includes_baseline():
    engine = PQCEngine(max_branches=1, max_iterations=2)
    ticket = Ticket(
        title="Add solve helper for baseline demo",
        description="Implement a small solve() helper that returns True so tests can pass.",
        acceptance_criteria=["solve returns true"],
    )
    report = engine.run(ticket)
    assert report.status.value in ("production_qualified", "needs_review", "failed")
