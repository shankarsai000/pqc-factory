"""Tests for LangGraph PQC pipeline."""

from pqc_factory.models.ticket import Ticket
from pqc_factory.models.pqc_report import PQCStatus
from pqc_factory.orchestrator.graph import build_pqc_graph, run_via_graph, graph_mermaid


def test_graph_mermaid():
    md = graph_mermaid()
    assert "plan" in md
    assert "fork_branches" in md
    assert "mermaid" in md


def test_run_via_graph():
    ticket = Ticket(
        title="Add a simple utility function",
        description="Create a small helper that returns True. Enough text for validation.",
        acceptance_criteria=["works"],
        max_iterations=2,
    )
    report = run_via_graph(ticket, max_branches=2, max_iterations=2)
    assert report.status in (PQCStatus.PRODUCTION_QUALIFIED, PQCStatus.NEEDS_REVIEW, PQCStatus.FAILED)
    assert report.branches_evaluated >= 1 or report.status == PQCStatus.FAILED
