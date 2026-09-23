"""Branch scoring logic."""

from __future__ import annotations

from typing import Dict, List

from pqc_factory.models.metrics import BranchMetrics


def score_branches(metrics_list: List[BranchMetrics]) -> Dict[str, float]:
    """Compute overall scores and return mapping branch_id → score."""
    scores = {}
    for m in metrics_list:
        m.compute_overall()
        scores[m.branch_id] = m.overall_score
    return scores


def select_winner(metrics_list: List[BranchMetrics]) -> BranchMetrics | None:
    if not metrics_list:
        return None
    score_branches(metrics_list)
    return max(metrics_list, key=lambda m: m.overall_score)
