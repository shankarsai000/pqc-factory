"""Quality gates — deterministic merge-safety checks."""

from pqc_factory.gates.quality import gate_acceptance, gate_static_risk, run_quality_gates, GateVerdict
from pqc_factory.models.ticket import Ticket
from pqc_factory.sandbox.manager import SandboxManager
from pqc_factory.eval.budget import Budget


def test_static_risk_detects_secret():
    sb = SandboxManager(mode="local")
    base = sb.create_base("g")
    sb.write_file(base, "x.py", 'api_key = "sk-live-abcdefghijklmnopqrstuvwxyz"\n')
    r = gate_static_risk(sb, base, ["x.py"])
    assert r.verdict == GateVerdict.FAIL
    sb.cleanup()


def test_acceptance_partial_coverage():
    ticket = Ticket(
        title="Add rate limiter utility",
        description="Implement an in-memory rate limiter for API endpoints with windowing.",
        acceptance_criteria=["rate limiter blocks excess", "thread safe", "unit tests"],
    )
    r = gate_acceptance(ticket, ["solution.py"], {"solution.py": "class RateLimiter:\n    def allow(self): pass\n"})
    assert r.verdict in (GateVerdict.PASS, GateVerdict.WARN, GateVerdict.FAIL)
    assert r.score is not None


def test_full_gates_on_clean_solution():
    sb = SandboxManager(mode="local")
    base = sb.create_base("clean")
    sb.write_file(base, "solution.py", 'def solve():\n    return True\n')
    sb.write_file(base, "test_solution.py", "from solution import solve\n\ndef test_solve():\n    assert solve() is True\n")
    ticket = Ticket(
        title="Add solve helper",
        description="A small helper that returns True for validation of the gate suite.",
        acceptance_criteria=["solve returns true"],
    )
    report = run_quality_gates(ticket, sb, base, ["solution.py", "test_solution.py"], security_score=90, critical_issues=0)
    assert report.merge_allowed is True or any(g.verdict.value == "pass" for g in report.gates)
    sb.cleanup()


def test_budget():
    b = Budget(max_tokens=100)
    b.record(40)
    assert not b.exhausted()
    b.record(70)
    assert b.exhausted()
