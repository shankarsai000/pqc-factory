"""Planner that decides parallel approaches - biased by learning memory."""

from __future__ import annotations

from typing import List

from pqc_factory.models.ticket import Ticket

DEFAULT_APPROACHES = [
    "minimal-direct",
    "defensive-robust",
    "clean-architecture",
]


def plan_approaches(
    ticket: Ticket,
    max_branches: int = 3,
    memory=None,
) -> List[str]:
    max_b = max(1, min(max_branches, 3))
    if memory is not None:
        try:
            return memory.preferred_approaches(
                title=ticket.title,
                description=ticket.description,
                language=getattr(ticket, "language", "python") or "python",
                default=DEFAULT_APPROACHES,
                max_branches=max_b,
            )
        except Exception:
            pass
    return DEFAULT_APPROACHES[:max_b]
