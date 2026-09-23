"""CLI entry point for the PQC Factory - Claude Code-style terminal UX."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from pqc_factory.cli.brand import (
    VERSION,
    footer_rule,
    header_rule,
    info_panel,
    print_logo,
    result_panel,
    stage_line,
    ticket_panel,
    welcome_block,
)
from pqc_factory.models.ticket import Ticket

app = typer.Typer(
    name="pqc",
    help="Production-Qualified Change Factory",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=False,
)
console = Console(highlight=False)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """PQC Factory - agentic production-qualified changes."""
    if ctx.invoked_subcommand is None:
        welcome_block(console)


@app.command()
def run(
    ticket: Path = typer.Option(..., "--ticket", "-t", help="Path to ticket JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run the full PQC pipeline on a ticket."""
    print_logo(console, compact=True)
    header_rule(console, "run")

    data = json.loads(ticket.read_text(encoding="utf-8"))
    t = Ticket(**data)

    console.print(ticket_panel(t.title, extra=f"  lang={t.language}  risk={t.risk_tolerance.value}"))
    if verbose:
        console.print(Panel(t.summary(), border_style="dim", title="[dim]summary[/dim]"))

    console.print()
    console.print(stage_line("plan", "Nemotron approaches"))
    console.print(stage_line("fork", "sandbox branches"))
    console.print(stage_line("implement <-> verify", "agent loops"))
    console.print(stage_line("security + performance", "gates"))
    console.print(stage_line("score + report", "PQC package"))
    console.print()

    from pqc_factory.orchestrator.engine import PQCEngine

    with console.status("[cyan]◆[/cyan] Running PQC pipeline...", spinner="dots"):
        engine = PQCEngine()
        report = engine.run(t)

    console.print()
    console.print(
        result_panel(
            status=report.status.value,
            score=report.overall_score,
            risk=report.risk_score,
            branches=report.branches_evaluated,
            pr_ready=report.pr_ready,
        )
    )
    console.print()
    console.print(
        Panel(
            Markdown(report.to_markdown()),
            border_style="dim",
            title="[bold]PQC Report[/bold]",
            title_align="left",
            padding=(1, 2),
        )
    )

    out = Path("pqc_report.md")
    out.write_text(report.to_markdown(), encoding="utf-8")
    console.print()
    console.print(f"  [green]✓[/green] Report written to [bold]{out}[/bold]")
    footer_rule(console)


@app.command()
def status():
    """Show environment + branding status."""
    print_logo(console, compact=True)
    header_rule(console, "status")
    console.print(info_panel(
        f"[bold]PQC Factory[/bold] v{VERSION}\n"
        "[dim]Sandbox · Agents · Policy · HITL · Memory[/dim]\n\n"
        "Ready. Try: [cyan]pqc run -t pqc_factory/examples/sample_ticket.json[/cyan]",
        title="◆ status",
    ))
    footer_rule(console)


@app.command()
def report(path: Path = typer.Argument("pqc_report.md")):
    """Display a previously generated report."""
    print_logo(console, compact=True)
    if not path.exists():
        console.print(info_panel(f"[red]File not found:[/red] {path}", title="error", style="red"))
        raise typer.Exit(1)
    console.print(
        Panel(
            Markdown(path.read_text(encoding="utf-8")),
            border_style="cyan",
            title="[bold]PQC Report[/bold]",
            padding=(1, 2),
        )
    )
    footer_rule(console)


@app.command("pr")
def pr_package(
    ticket: Path = typer.Option(..., "--ticket", "-t"),
    out: Path = typer.Option(Path("./pqc_pr"), "--out", "-o"),
):
    """Run pipeline and emit a PR package."""
    print_logo(console, compact=True)
    header_rule(console, "pr package")
    from pqc_factory.orchestrator.graph import run_via_graph
    from pqc_factory.pr.package import build_pr_package

    data = json.loads(ticket.read_text(encoding="utf-8"))
    t = Ticket(**data)
    with console.status("[cyan]◆[/cyan] Building PR package...", spinner="dots"):
        report = run_via_graph(t, max_branches=2, max_iterations=3)
        pkg = build_pr_package(t, report)
        path = pkg.write(out)
    console.print(info_panel(
        f"[bold]Branch[/bold]   {pkg.branch_name}\n"
        f"[bold]PR ready[/bold] {pkg.pr_ready}\n"
        f"[bold]Out[/bold]      {path}",
        title="◆ PR package",
        style="green" if pkg.pr_ready else "yellow",
    ))
    footer_rule(console)


@app.command("replay")
def replay(
    log: Path = typer.Option(Path("/tmp/pqc_logs/decisions.jsonl"), "--log", "-l"),
):
    """Replay a decision log with Rich output."""
    print_logo(console, compact=True)
    header_rule(console, "replay")
    from pqc_factory.cli.progress import replay_decision_log

    replay_decision_log(log)
    footer_rule(console)


@app.command("graph")
def show_graph():
    """Print Mermaid diagram of the PQC LangGraph."""
    print_logo(console, compact=True)
    header_rule(console, "graph")
    from pqc_factory.orchestrator.graph import graph_mermaid

    console.print(Panel(graph_mermaid(), border_style="cyan", title="[bold]LangGraph[/bold]"))
    footer_rule(console)


@app.command("approve")
def approve(
    run_id: str = typer.Argument(..., help="HITL run id"),
    reason: str = typer.Option("approved by human", "--reason", "-r"),
):
    """Approve a pending high-risk PQC run."""
    print_logo(console, compact=True)
    from pqc_factory.hitl.gates import HITLStore

    store = HITLStore()
    try:
        g = store.approve(run_id, reason=reason)
        console.print(info_panel(
            f"[green]APPROVED[/green]  {g.run_id}\n{g.reason}",
            title="◆ HITL",
            style="green",
        ))
    except KeyError:
        console.print(info_panel(f"[red]Unknown run_id:[/red] {run_id}", title="error", style="red"))
        raise typer.Exit(1)


@app.command("reject")
def reject(
    run_id: str = typer.Argument(...),
    reason: str = typer.Option(..., "--reason", "-r"),
    feedback: str = typer.Option("", "--feedback", "-f"),
):
    """Reject a pending run; feedback for next implementer loop."""
    print_logo(console, compact=True)
    from pqc_factory.hitl.gates import HITLStore

    store = HITLStore()
    try:
        g = store.reject(run_id, reason=reason, feedback=feedback)
        console.print(info_panel(
            f"[red]REJECTED[/red]  {g.run_id}\n{g.feedback or g.reason}",
            title="◆ HITL",
            style="red",
        ))
    except KeyError:
        console.print(info_panel(f"[red]Unknown run_id:[/red] {run_id}", title="error", style="red"))
        raise typer.Exit(1)


@app.command("pending")
def pending():
    """List pending human-in-the-loop gates."""
    print_logo(console, compact=True)
    header_rule(console, "pending gates")
    from pqc_factory.hitl.gates import HITLStore

    items = HITLStore().list_pending()
    if not items:
        console.print("  [dim]No pending gates[/dim]")
        footer_rule(console)
        return
    for g in items:
        console.print(
            f"  [yellow]◆[/yellow] [bold]{g.run_id}[/bold]  "
            f"risk={g.risk_score}  score={g.overall_score:.1f}  [dim]{g.ticket_title}[/dim]"
        )
    footer_rule(console)


if __name__ == "__main__":
    app()
