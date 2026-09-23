"""Tests for data models."""

from pqc_factory.models.ticket import Ticket, RiskTolerance
from pqc_factory.models.metrics import BranchMetrics
from pqc_factory.models.pqc_report import PQCReport, PQCStatus


def test_ticket_creation():
    t = Ticket(
        title="Test ticket title",
        description="A sufficiently long description for validation purposes.",
        acceptance_criteria=["crit1"],
    )
    assert t.risk_tolerance == RiskTolerance.MEDIUM
    assert "Test ticket" in t.summary()


def test_branch_metrics_scoring():
    m = BranchMetrics(
        branch_id="b1",
        test_pass_rate=1.0,
        security_score=90,
        performance_score=80,
        code_quality_score=85,
        critical_security_issues=0,
    )
    score = m.compute_overall()
    assert score > 80
    assert m.overall_score == score


def test_pqc_report_markdown():
    r = PQCReport(
        status=PQCStatus.PRODUCTION_QUALIFIED,
        ticket_title="Demo",
        overall_score=88.5,
        risk_score=20,
        summary="Looks good",
    )
    md = r.to_markdown()
    assert "Production-Qualified Change Report" in md
    assert "88.5" in md
