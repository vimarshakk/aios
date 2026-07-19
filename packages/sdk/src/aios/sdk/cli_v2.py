"""AIOS CLI v2 — Interactive mode, plugin management, and knowledge graph commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from aios.plugins.dependencies import DependencyResolver
from aios.plugins.marketplace import MarketplaceEntry, PluginMarketplace
from aios.plugins.versions import SemVer, VersionRange, is_compatible
from aios.security.audit import AuditLogger
from aios.security.rate_limiter import RateLimiter, SlidingWindowLimiter

console = Console()

v2 = typer.Typer(help="AIOS CLI v2", no_args_is_help=True)

DEFAULT_DATA_DIR = Path.home() / ".aios"


def _marketplace(data_dir: Path | None = None) -> PluginMarketplace:
    d = data_dir or DEFAULT_DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    return PluginMarketplace(storage_path=d / "marketplace.json")


def _audit() -> AuditLogger:
    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return AuditLogger(storage_path=DEFAULT_DATA_DIR / "audit.jsonl")


# ─── Plugin Commands ──────────────────────────


@v2.command("plugin")
def plugin_list(
    data_dir: Path | None = typer.Option(None, "--data-dir", "-d"),  # noqa: B008
) -> None:
    """List all installed plugins."""
    mp = _marketplace(data_dir)
    installed = mp.list_installed()
    if not installed:
        console.print("[dim]No plugins installed.[/dim]")
        return
    table = Table(title="Installed Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Author")
    for e in installed:
        table.add_row(e.name, str(e.version), e.author)
    console.print(table)


@v2.command("plugin-search")
def plugin_search(
    query: str = typer.Argument(help="Search query"),
    data_dir: Path | None = typer.Option(None, "--data-dir", "-d"),  # noqa: B008
) -> None:
    """Search plugins in the registry."""
    mp = _marketplace(data_dir)
    results = mp.search(query)
    if not results:
        console.print(f"[dim]No plugins found for '{query}'.[/dim]")
        return
    table = Table(title=f"Search: {query}")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Author")
    table.add_column("Description")
    for e in results:
        table.add_row(e.name, str(e.version), e.author, e.description)
    console.print(table)


@v2.command("plugin-install")
def plugin_install(
    name: str = typer.Argument(help="Plugin name"),
    data_dir: Path | None = typer.Option(None, "--data-dir", "-d"),  # noqa: B008
) -> None:
    """Install a plugin from the marketplace."""
    mp = _marketplace(data_dir)
    audit = _audit()
    try:
        if not mp.search(name):
            entry = MarketplaceEntry(name=name, version=SemVer(1, 0, 0), author="cli")
            mp.publish(entry)
        entry = mp.install(name)
        details = {"version": str(entry.version)}
        audit.log("plugin.install", actor="cli", target=name, details=details)
        console.print(f"[green]Installed {name} v{entry.version}[/green]")
    except Exception as exc:
        err_details = {"error": str(exc)}
        audit.log(
            "plugin.install", actor="cli", target=name,
            success=False, details=err_details,
        )
        console.print(f"[red]Install failed: {exc}[/red]")
        raise typer.Exit(1) from exc


@v2.command("plugin-remove")
def plugin_remove(
    name: str = typer.Argument(help="Plugin name"),
    data_dir: Path | None = typer.Option(None, "--data-dir", "-d"),  # noqa: B008
) -> None:
    """Uninstall a plugin."""
    mp = _marketplace(data_dir)
    audit = _audit()
    try:
        mp.uninstall(name)
        audit.log("plugin.remove", actor="cli", target=name)
        console.print(f"[green]Removed {name}[/green]")
    except Exception as exc:
        err_details = {"error": str(exc)}
        audit.log(
            "plugin.remove", actor="cli", target=name,
            success=False, details=err_details,
        )
        console.print(f"[red]Remove failed: {exc}[/red]")
        raise typer.Exit(1) from exc


# ─── Version Commands ─────────────────────────


@v2.command("version-check")
def version_check(
    version_a: str = typer.Argument(help="First version (e.g. 1.2.3)"),
    constraint: str = typer.Argument(help="Version range (e.g. >=1.0.0)"),
) -> None:
    """Check if a version satisfies a range constraint."""
    sem = SemVer.parse(version_a)
    vr = VersionRange(expression=constraint)
    result = is_compatible(str(sem), vr.expression)
    label = "compatible" if result else "not compatible"
    console.print(f"{sem} is {label} with {vr.expression}")


@v2.command("version-compare")
def version_compare(
    version_a: str = typer.Argument(help="First version"),
    version_b: str = typer.Argument(help="Second version"),
) -> None:
    """Compare two semantic versions."""
    a = SemVer.parse(version_a)
    b = SemVer.parse(version_b)
    if a < b:
        console.print(f"{a} < {b}")
    elif a > b:
        console.print(f"{a} > {b}")
    else:
        console.print(f"{a} == {b}")


# ─── Dependency Commands ──────────────────────


@v2.command("deps-check")
def deps_check(
    data_dir: Path | None = typer.Option(None, "--data-dir", "-d"),  # noqa: B008
) -> None:
    """Check plugin dependency graph for issues."""
    mp = _marketplace(data_dir)
    installed = mp.list_installed()
    if not installed:
        console.print("[dim]No plugins installed.[/dim]")
        return

    resolver = DependencyResolver()
    graph: dict[str, list[str]] = {}
    for e in installed:
        graph[e.name] = [d.name for d in e.dependencies]

    errors = resolver.validate(graph)
    if not errors:
        console.print("[green]All dependencies resolved.[/green]")
        return
    for err in errors:
        console.print(f"[red]{err}[/red]")


# ─── Security Commands ────────────────────────


@v2.command("rate-status")
def rate_status() -> None:
    """Show rate limiter configuration."""
    rl = RateLimiter(capacity=100, refill_rate=10.0)
    sw = SlidingWindowLimiter(max_requests=1000, window_seconds=60.0)
    console.print("[bold]Rate Limiters[/bold]")
    console.print(f"  Token Bucket: capacity={rl.capacity}, refill={rl.refill_rate}/s")
    console.print(f"  Sliding Window: max={sw.max_requests}, window={sw.window_seconds}s")


@v2.command("audit-log")
def audit_log_cmd(
    limit: int = typer.Option(20, "--limit", "-n"),
    level: str | None = typer.Option(None, "--level", "-l"),
    data_dir: Path | None = typer.Option(None, "--data-dir", "-d"),  # noqa: B008
) -> None:
    """Show recent audit log entries."""
    from aios.security.audit import AuditLevel

    al = AuditLogger(storage_path=(data_dir or DEFAULT_DATA_DIR) / "audit.jsonl")
    lv = AuditLevel(level) if level else None
    events = al.query(level=lv, limit=limit)
    if not events:
        console.print("[dim]No audit events.[/dim]")
        return

    level_styles = {
        "info": "green",
        "warning": "yellow",
        "error": "red",
        "critical": "bold red",
    }
    table = Table(title="Audit Log")
    table.add_column("Time", style="dim")
    table.add_column("Level")
    table.add_column("Action", style="cyan")
    table.add_column("Actor")
    table.add_column("Target")
    for e in events:
        style = level_styles.get(e.level.value, "")
        table.add_row(
            f"{e.timestamp:.0f}",
            f"[{style}]{e.level.value}[/{style}]",
            e.action,
            e.actor,
            e.target,
        )
    console.print(table)


# ─── Interactive Shell ─────────────────────────


HELP_TEXT = (
    "Commands:\n"
    "  plugin          List installed plugins\n"
    "  plugin-search   Search for plugins\n"
    "  plugin-install  Install a plugin\n"
    "  plugin-remove   Remove a plugin\n"
    "  version-check   Check version compatibility\n"
    "  deps-check      Check dependency graph\n"
    "  rate-status     Show rate limiter config\n"
    "  audit-log       Show audit entries\n"
    "  help            Show this help\n"
    "  exit            Exit shell\n"
)


@v2.command("shell")
def shell() -> None:
    """Start an interactive AIOS shell."""
    console.print("[bold cyan]AIOS Interactive Shell[/bold cyan]")
    console.print("Type [green]help[/green] for commands, [green]exit[/green] to quit.\n")
    while True:
        try:
            line = console.input("[bold]>[/bold] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        stripped = line.strip()
        if not stripped:
            continue
        if stripped in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if stripped == "help":
            console.print(HELP_TEXT)
            continue
        console.print(f"[yellow]Unknown command:[/yellow] {stripped}. Type 'help'.")
