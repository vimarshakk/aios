"""AIOS CLI — command-line interface for interacting with the AIOS gateway."""

from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="aios",
    help="AIOS — Personal AI Operating System",
    no_args_is_help=True,
)
console = Console()

DEFAULT_URL = "http://localhost:8080"


def _get_url() -> str:
    import os
    return os.environ.get("AIOS_GATEWAY_URL", DEFAULT_URL)


@app.command()
def chat(
    message: str = typer.Argument(help="Message to send"),
    agent: str | None = typer.Option(None, "--agent", "-a", help="Agent name"),
    session: str | None = typer.Option(None, "--session", "-s", help="Session ID"),
) -> None:
    """Send a chat message to AIOS."""
    url = _get_url()
    payload: dict = {"message": message}
    if agent:
        payload["agent"] = agent
    if session:
        payload["session_id"] = session

    resp = httpx.post(f"{url}/chat", json=payload, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    console.print(f"[bold green]{data['response']}[/bold green]")
    if data.get("session_id"):
        console.print(f"[dim]session: {data['session_id']}[/dim]")


@app.command("agent")
def agent_list() -> None:
    """List registered agents."""
    url = _get_url()
    resp = httpx.get(f"{url}/agents", timeout=10.0)
    resp.raise_for_status()
    agents = resp.json()
    if not agents:
        console.print("[dim]No agents registered.[/dim]")
        return
    table = Table(title="Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    for a in agents:
        table.add_row(a["name"], a["type"])
    console.print(table)


@app.command("tool")
def tool_list() -> None:
    """List registered tools."""
    url = _get_url()
    resp = httpx.get(f"{url}/tools", timeout=10.0)
    resp.raise_for_status()
    tools = resp.json()
    if not tools:
        console.print("[dim]No tools registered.[/dim]")
        return
    table = Table(title="Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Category", style="magenta")
    for t in tools:
        table.add_row(t["name"], t["description"], t["category"])
    console.print(table)


@app.command("provider")
def provider_list() -> None:
    """List configured providers."""
    from aios.providers.factory import create_engine
    table = Table(title="Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    for name in ("ollama", "openai", "anthropic"):
        try:
            create_engine(name)
            status = "available"
        except Exception:
            status = "not configured"
        table.add_row(name, status)
    console.print(table)


@app.command()
def status() -> None:
    """Show AIOS system status."""
    url = _get_url()
    try:
        resp = httpx.get(f"{url}/health", timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        console.print(f"[green]Gateway: OK[/green] (v{data['version']})")
        console.print(f"  Agents: {len(data['agents'])}")
        console.print(f"  Tools:  {len(data['tools'])}")
    except Exception as exc:
        console.print(f"[red]Gateway: unreachable ({exc})[/red]")


@app.command()
def config(
    key: str = typer.Argument(help="Config key (e.g. 'provider')"),
    value: str = typer.Argument(help="Config value"),
) -> None:
    """Set a configuration value."""
    console.print(f"Config set: [cyan]{key}[/cyan] = [green]{value}[/green]")
    console.print("[dim](Note: config persistence coming in M2)[/dim]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """AIOS — Personal AI Operating System."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
