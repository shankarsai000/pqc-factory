from pqc_factory.models.ticket import Ticket
from pqc_factory.orchestrator.engine import PQCEngine
from pqc_factory.models.pqc_report import PQCStatus


def test_full_pipeline_local():
    ticket = Ticket(
        title="Add a simple utility function",
        description="Create a small helper that returns True. This is a local-mode test ticket with enough text.",
        acceptance_criteria=["A function exists", "It returns True"],
        max_iterations=2,
    )
    engine = PQCEngine(max_branches=2, max_iterations=2)
    report = engine.run(ticket)
    assert report.status in (PQCStatus.PRODUCTION_QUALIFIED, PQCStatus.NEEDS_REVIEW)
    assert report.branches_evaluated >= 1
    assert report.overall_score > 0
