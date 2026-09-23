"""CLI entry point for the PQC Factory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from pqc_factory.models.ticket import Ticket
from pqc_factory.orchestrator.engine import PQCEngine

app = typer.Typer(help="Production-Qualified Change Factory")
console = Console()


@app.command()
def run(
    ticket: Path = typer.Option(..., "--ticket", "-t", help="Path to ticket JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run the full PQC pipeline on a ticket."""
    data = json.loads(ticket.read_text(encoding="utf-8"))
    t = Ticket(**data)

    console.print(Panel(f"[bold]Ticket:[/bold] {t.title}", title="PQC Factory"))
    if verbose:
        console.print(t.summary())

    engine = PQCEngine()
    report = engine.run(t)

    console.print()
    console.print(
        Panel(
            f"Status: [bold]{report.status.value}[/bold]\n"
            f"Score:  {report.overall_score:.1f}/100\n"
            f"Risk:   {report.risk_score}/100\n"
            f"Branches evaluated: {report.branches_evaluated}",
            title="Result",
        )
    )
    console.print(Markdown(report.to_markdown()))

    out = Path("pqc_report.md")
    out.write_text(report.to_markdown(), encoding="utf-8")
    console.print(f"\n[green]Report written to {out}[/green]")


@app.command()
def status():
    """Show basic environment status."""
    console.print("PQC Factory CLI is ready.")
    console.print("Use: pqc run --ticket examples/sample_ticket.json")


@app.command()
def report(path: Path = typer.Argument("pqc_report.md")):
    """Display a previously generated report."""
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)
    console.print(Markdown(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    app()
