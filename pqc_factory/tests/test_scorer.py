from pqc_factory.models.metrics import BranchMetrics
from pqc_factory.orchestrator.scorer import score_branches, select_winner


def test_select_winner():
    m1 = BranchMetrics(branch_id="a", test_pass_rate=0.5, security_score=60, performance_score=60, code_quality_score=60)
    m2 = BranchMetrics(branch_id="b", test_pass_rate=1.0, security_score=95, performance_score=90, code_quality_score=90)
    m1.compute_overall()
    m2.compute_overall()
    winner = select_winner([m1, m2])
    assert winner is not None
    assert winner.branch_id == "b"
