#!/usr/bin/env python3
"""End-to-end demo of the Production-Qualified Change Factory (local mode)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pqc_factory.models.ticket import Ticket
from pqc_factory.orchestrator.engine import PQCEngine


def main() -> None:
    ticket_path = ROOT / "pqc_factory" / "examples" / "sample_ticket.json"
    data = json.loads(ticket_path.read_text(encoding="utf-8"))
    ticket = Ticket(**data)

    print("=" * 60)
    print("PQC FACTORY — END-TO-END DEMO (local mode)")
    print("=" * 60)
    print(f"Ticket: {ticket.title}")
    print()

    engine = PQCEngine(max_branches=2, max_iterations=3)
    report = engine.run(ticket)

    print("-" * 60)
    print(f"Status:     {report.status.value}")
    print(f"Score:      {report.overall_score:.1f}/100")
    print(f"Risk:       {report.risk_score}/100")
    print(f"Branches:   {report.branches_evaluated}")
    print(f"Winner:     {report.winner_branch_id}")
    print(f"Approach:   {report.winner_approach}")
    print(f"PR ready:   {report.pr_ready}")
    print("-" * 60)
    print()
    print(report.to_markdown())

    out = ROOT / "pqc_report.md"
    out.write_text(report.to_markdown(), encoding="utf-8")
    print()
    print(f"Report written to {out}")


if __name__ == "__main__":
    main()
