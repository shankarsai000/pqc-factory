"""Live Rich progress + decision-log replay for demos."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


def live_run_progress(steps: List[str], delay: float = 0.15) -> None:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
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
    table = Table(title="Branch scores")
    table.add_column("Branch")
    table.add_column("Score", justify="right")
    table.add_column("Winner")
    for bid, score in sorted(scores.items(), key=lambda x: -x[1]):
        mark = "*" if bid == winner else ""
        table.add_row(bid[:40], f"{score:.1f}", mark)
    return table


def replay_decision_log(path: str | Path, delay: float = 0.05) -> None:
    p = Path(path)
    if not p.exists():
        console.print(f"[red]Log not found: {p}[/red]")
        return
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    console.print(Panel(f"Replaying {len(lines)} events from {p}", title="PQC Replay"))
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = rec.get("event", "?")
        data = rec.get("data", {})
        ts = rec.get("ts", "")[:19]
        console.print(f"[dim]{ts}[/dim] [cyan]{event}[/cyan] {data}")
        time.sleep(delay)
    console.print("[green]Replay complete[/green]")


def iter_log(path: str | Path) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            yield json.loads(line)
