"""CLI entry point for the PQC Factory."""

from __future__ import annotations

import json
from pathlib import Path

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
    console.print("PQC Factory CLI is ready.")


@app.command()
def report(path: Path = typer.Argument("pqc_report.md")):
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)
    console.print(Markdown(path.read_text(encoding="utf-8")))


@app.command("pr")
def pr_package(
    ticket: Path = typer.Option(..., "--ticket", "-t"),
    out: Path = typer.Option(Path("./pqc_pr"), "--out", "-o"),
):
    from pqc_factory.pr.package import build_pr_package
    from pqc_factory.orchestrator.graph import run_via_graph
    data = json.loads(ticket.read_text(encoding="utf-8"))
    t = Ticket(**data)
    report = run_via_graph(t, max_branches=2, max_iterations=3)
    pkg = build_pr_package(t, report)
    path = pkg.write(out)
    console.print(Panel(
        f"Branch: {pkg.branch_name}\nPR ready: {pkg.pr_ready}\nOut: {path}",
        title="PR Package",
    ))


@app.command("replay")
def replay(
    log: Path = typer.Option(Path("/tmp/pqc_logs/decisions.jsonl"), "--log", "-l"),
):
    from pqc_factory.cli.progress import replay_decision_log
    replay_decision_log(log)


@app.command("graph")
def show_graph():
    from pqc_factory.orchestrator.graph import graph_mermaid
    console.print(graph_mermaid())


@app.command("approve")
def approve(
    run_id: str = typer.Argument(..., help="HITL run id"),
    reason: str = typer.Option("approved by human", "--reason", "-r"),
):
    from pqc_factory.hitl.gates import HITLStore
    store = HITLStore()
    try:
        g = store.approve(run_id, reason=reason)
        console.print(Panel(f"[green]APPROVED[/green] {g.run_id}\n{g.reason}", title="HITL"))
    except KeyError:
        console.print(f"[red]Unknown run_id: {run_id}[/red]")
        raise typer.Exit(1)


@app.command("reject")
def reject(
    run_id: str = typer.Argument(...),
    reason: str = typer.Option(..., "--reason", "-r"),
    feedback: str = typer.Option("", "--feedback", "-f"),
):
    from pqc_factory.hitl.gates import HITLStore
    store = HITLStore()
    try:
        g = store.reject(run_id, reason=reason, feedback=feedback)
        console.print(Panel(f"[red]REJECTED[/red] {g.run_id}\n{g.feedback or g.reason}", title="HITL"))
    except KeyError:
        console.print(f"[red]Unknown run_id: {run_id}[/red]")
        raise typer.Exit(1)


@app.command("pending")
def pending():
    from pqc_factory.hitl.gates import HITLStore
    items = HITLStore().list_pending()
    if not items:
        console.print("[dim]No pending gates[/dim]")
        return
    for g in items:
        console.print(f"[yellow]{g.run_id}[/yellow] risk={g.risk_score} score={g.overall_score:.1f} - {g.ticket_title}")


if __name__ == "__main__":
    app()
