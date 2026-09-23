"""PQC Factory terminal branding - Claude Code-style logo and chrome."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

ACCENT = "bold cyan"
MUTED = "dim"
OK = "bold green"
WARN = "bold yellow"
ERR = "bold red"
TITLE = "bold white"

LOGO_BANNER = r"""
  ██████╗  ██████╗  ██████╗
  ██╔══██╗██╔═══██╗██╔════╝
  ██████╔╝██║   ██║██║     
  ██╔═══╝ ██║▄▄ ██║██║     
  ██║     ╚██████╔╝╚██████╗
  ╚═╝      ╚══▀▀═╝  ╚═════╝
""".strip("\n")

LOGO_WORDMARK = r"""
 ╔══════════════════════════╗
 ║  ◆  P Q C   F A C T O R Y ║
 ╚══════════════════════════╝
""".strip("\n")

TAGLINE = "Production-Qualified Change  ·  Nebius × Nemotron"
VERSION = "0.2.0"


def get_console() -> Console:
    return Console(highlight=False, soft_wrap=True)


def print_logo(console: Console | None = None, compact: bool = False) -> None:
    c = console or get_console()
    art = LOGO_WORDMARK if compact else LOGO_BANNER
    logo = Text(art, style=ACCENT)
    c.print()
    c.print(Align.center(logo))
    c.print(Align.center(Text(TAGLINE, style=MUTED)))
    c.print(Align.center(Text(f"v{VERSION}", style=MUTED)))
    c.print()


def header_rule(console: Console | None = None, label: str = "PQC Factory") -> None:
    c = console or get_console()
    c.print(Rule(f"[cyan]◆[/cyan] [bold]{label}[/bold]", style="cyan"))


def footer_rule(console: Console | None = None) -> None:
    c = console or get_console()
    c.print(Rule(style="dim"))


def badge(status: str) -> Text:
    s = (status or "").lower()
    if "production" in s or "qualified" in s or s in ("pass", "approved", "ok"):
        return Text(f" ● {status} ", style="bold white on green")
    if "review" in s or "pending" in s or "warn" in s:
        return Text(f" ● {status} ", style="bold black on yellow")
    if "fail" in s or "reject" in s or "error" in s:
        return Text(f" ● {status} ", style="bold white on red")
    return Text(f" ● {status} ", style="bold white on blue")


def ticket_panel(title: str, extra: str = "") -> Panel:
    body = Text()
    body.append("  Ticket  ", style="bold black on cyan")
    body.append(f"  {title}\n", style="bold")
    if extra:
        body.append(extra, style=MUTED)
    return Panel(
        body,
        border_style="cyan",
        title="[bold cyan]◆ PQC[/bold cyan]",
        title_align="left",
        subtitle="[dim]pipeline[/dim]",
        subtitle_align="right",
        padding=(1, 2),
    )


def result_panel(
    status: str,
    score: float,
    risk: int,
    branches: int,
    pr_ready: bool = False,
) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column(style="bold")
    table.add_row("Status", badge(status))
    table.add_row("Score", f"[{OK if score >= 70 else WARN}]{score:.1f}[/]/100")
    table.add_row("Risk", f"[{OK if risk <= 40 else WARN}]{risk}[/]/100")
    table.add_row("Branches", str(branches))
    table.add_row("PR ready", f"[{OK}]yes[/]" if pr_ready else f"[{MUTED}]no[/]")
    return Panel(
        table,
        border_style="green" if score >= 70 and risk <= 40 else "yellow",
        title="[bold]Result[/bold]",
        title_align="left",
        padding=(1, 2),
    )


def info_panel(message: str, title: str = "Info", style: str = "cyan") -> Panel:
    return Panel(
        message,
        border_style=style,
        title=f"[bold]{title}[/bold]",
        title_align="left",
        padding=(0, 2),
    )


def stage_line(stage: str, detail: str = "", done: bool = False) -> Text:
    mark = "✓" if done else "→"
    style = OK if done else ACCENT
    t = Text()
    t.append(f"  {mark} ", style=style)
    t.append(f"{stage}", style="bold" if not done else MUTED)
    if detail:
        t.append(f"  {detail}", style=MUTED)
    return t


def welcome_block(console: Console | None = None) -> None:
    c = console or get_console()
    print_logo(c, compact=True)
    tips = Table.grid(padding=(0, 2))
    tips.add_column(style="cyan", justify="right")
    tips.add_column(style="dim")
    tips.add_row("pqc run -t ticket.json", "Run full pipeline")
    tips.add_row("pqc graph", "Show LangGraph diagram")
    tips.add_row("pqc pending", "HITL gates waiting")
    tips.add_row("pqc pr -t ticket.json", "Emit PR package")
    c.print(Panel(tips, border_style="dim", title="[dim]commands[/dim]", padding=(1, 2)))
    footer_rule(c)
