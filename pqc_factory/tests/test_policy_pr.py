"""Tests for policy packs and PR package."""

from pqc_factory.models.metrics import BranchMetrics
from pqc_factory.models.pqc_report import PQCReport, PQCStatus
from pqc_factory.models.ticket import Ticket
from pqc_factory.policy.rules import PolicyRules, load_policy
from pqc_factory.pr.package import build_pr_package


def test_policy_violations():
    rules = PolicyRules(min_overall_score=90, max_critical_security=0)
    m = BranchMetrics(
        branch_id="b1", test_pass_rate=1.0, security_score=50,
        overall_score=60, critical_security_issues=1,
    )
    m.compute_overall()
    v = rules.evaluate(m)
    assert any("critical" in x for x in v)


def test_policy_apply_downgrades():
    rules = PolicyRules(max_risk_score=10)
    report = PQCReport(
        status=PQCStatus.PRODUCTION_QUALIFIED, ticket_title="t",
        overall_score=95, risk_score=40, pr_ready=True,
    )
    out = rules.apply_to_report(report)
    assert out.status == PQCStatus.NEEDS_REVIEW
    assert out.pr_ready is False


def test_load_default_policy():
    assert load_policy().min_overall_score == 70


def test_pr_package():
    ticket = Ticket(
        title="Add rate limiter",
        description="A sufficiently long description for the ticket validation path.",
    )
    report = PQCReport(
        status=PQCStatus.PRODUCTION_QUALIFIED, ticket_title=ticket.title,
        overall_score=91.0, risk_score=25, pr_ready=True,
        changed_files=["solution.py"], summary="ok",
    )
    pkg = build_pr_package(ticket, report)
    assert pkg.branch_name.startswith("pqc/")
    assert "Add rate limiter" in pkg.pr_title
    assert pkg.pr_ready is True
