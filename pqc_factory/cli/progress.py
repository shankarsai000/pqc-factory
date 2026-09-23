"""Live Rich progress + decision-log replay - branded."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from pqc_factory.cli.brand import OK

console = Console(highlight=False)


def live_run_progress(steps: List[str], delay: float = 0.15) -> None:
    progress = Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]◆[/bold cyan] {task.description}"),
        BarColumn(bar_width=24, style="cyan", complete_style="green"),
        TimeElapsedColumn(),
        console=console,
    )
    with progress:
        task = progress.add_task("PQC pipeline", total=len(steps))
        for step in steps:
            progress.update(task, description=step)
            time.sleep(delay)
            progress.advance(task)


def render_scoreboard(scores: Dict[str, float], winner: Optional[str] = None) -> Table:
    table = Table(title="[cyan]◆[/cyan] Branch scores", border_style="dim")
    table.add_column("Branch")
    table.add_column("Score", justify="right")
    table.add_column("")
    for bid, score in sorted(scores.items(), key=lambda x: -x[1]):
        mark = "[green]★[/green]" if bid == winner else ""
        table.add_row(bid[:40], f"{score:.1f}", mark)
    return table


def replay_decision_log(path: str | Path, delay: float = 0.05) -> None:
    p = Path(path)
    if not p.exists():
        console.print(Panel(f"[red]Log not found:[/red] {p}", border_style="red", title="error"))
        return
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    console.print(
        Panel(
            f"Replaying [bold]{len(lines)}[/bold] events from [dim]{p}[/dim]",
            border_style="cyan",
            title="[bold cyan]◆ PQC Replay[/bold cyan]",
        )
    )
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = rec.get("event", "?")
        data = rec.get("data", {})
        ts = str(rec.get("ts", ""))[:19]
        console.print(f"  [dim]{ts}[/dim]  [cyan]→[/cyan] [bold]{event}[/bold]  [dim]{data}[/dim]")
        time.sleep(delay)
    console.print(f"  [{OK}]✓[/] [dim]Replay complete[/dim]")


def iter_log(path: str | Path) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            yield json.loads(line)
