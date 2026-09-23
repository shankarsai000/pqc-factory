"""Simple planner that decides parallel approaches."""

from __future__ import annotations

from typing import List

from pqc_factory.models.ticket import Ticket


def plan_approaches(ticket: Ticket, max_branches: int = 3) -> List[str]:
    """
    Return a short list of approach names to explore in parallel.
    In a full LLM-powered version this would call Nemotron-Ultra.
    """
    base = [
        "minimal-direct",
        "defensive-robust",
        "clean-architecture",
    ]
    return base[: max(1, min(max_branches, 3))]
