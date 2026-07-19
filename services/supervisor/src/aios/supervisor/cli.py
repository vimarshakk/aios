"""AIOS CLI — gateway-backed control surface (Priority 2, ADR-0027).

Thin, production-quality command-line front-end over the AIOS gateway's
external-control API (REST + ``WS /goals/ws``). Commands:

    <name> "objective"     submit a goal and follow it to completion
    <name> goals           list tracked goals
    <name> goal <id>       show one goal in detail
    <name> status [id]     summary of all goals or one goal
    <name> logs [id]       print the lifecycle events of a goal (or all)
    <name> watch           live-stream every goal from the global WS
    <name> pause <id>      pause a running goal
    <name> resume <id>     resume a paused / waiting-approval goal
    <name> cancel <id>     cancel a goal
    <name> retry <id>      retry a failed goal (fresh run of its objective)
    <name> version         print client + assistant version
    <name> doctor          check connectivity to the gateway

The assistant *name* is configurable (``AIOS_ASSISTANT_NAME`` env, default
``AIOS``) so the CLI can be rebranded without touching core code. Every
command supports ``--json`` for machine-readable output, and colors are used
only when stdout is a TTY (graceful fallback otherwise).

The CLI talks to the gateway at ``AIOS_GATEWAY_URL`` (default
``http://localhost:8080``) and reuses the existing ``Goal.to_dict`` wire
contract — no server-side API changes are required.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

try:
    import httpx2 as httpx
except ModuleNotFoundError:  # pragma: no cover - depends on install
    import httpx  # type: ignore[no-redef]

import websockets

__version__ = "0.6.6"

DEFAULT_GATEWAY = "http://localhost:8080"
TERMINAL = {"completed", "failed", "cancelled"}
STATUS_COLOR = {
    "pending": "yellow",
    "running": "blue",
    "paused": "yellow",
    "waiting_approval": "magenta",
    "completed": "green",
    "failed": "red",
    "cancelled": "red",
}


# --------------------------------------------------------------------------- config

def assistant_name() -> str:
    """Configurable assistant identity (rebrand without touching core code)."""
    return os.environ.get("AIOS_ASSISTANT_NAME", "AIOS")


def gateway_url() -> str:
    return os.environ.get("AIOS_GATEWAY_URL", DEFAULT_GATEWAY).rstrip("/")


def _ws_url() -> str:
    return gateway_url().replace("http", "ws")


# --------------------------------------------------------------------------- color

def _colorify(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    palette = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{palette.get(color, '')}{text}{palette['reset']}"


def _c(status: str) -> str:
    return _colorify(status, STATUS_COLOR.get(status, "reset"))


# --------------------------------------------------------------------------- output

def _emit_json(obj: Any) -> int:
    print(json.dumps(obj, indent=2, default=str))
    return 0


def _print_goal_row(g: dict[str, Any]) -> None:
    prog = g.get("progress", {})
    pct = prog.get("percent", 0)
    done = prog.get("completed", 0)
    total = prog.get("total_steps", 0)
    line = (
        f"  {_colorify(g['goal_id'], 'cyan'):<22} {_c(g['status']):<16} "
        f"{_colorify(f'{done}/{total}', 'bold')} "
        f"({pct}%)  {g.get('objective', '')[:52]}"
    )
    print(line)


def _print_goal_detail(g: dict[str, Any]) -> None:
    print(f"{_colorify('Goal', 'bold')}      {g['goal_id']}")
    print(f"Objective  {g.get('objective', '')}")
    print(f"Status     {_c(g['status'])}")
    prog = g.get("progress", {})
    print(f"Progress   {prog.get('completed', 0)}/{prog.get('total_steps', 0)} ({prog.get('percent', 0)}%)")
    if g.get("error"):
        print(f"Error      {_colorify(g['error'], 'red')}")
    graph = g.get("task_graph")
    if graph:
        tasks = graph.get("tasks", [])
        print(f"\n{_colorify('Tasks', 'bold')} ({len(tasks)}):")
        for t in tasks:
            mark = "+" if t.get("status") == "success" else ("!" if t.get("status") == "failed" else " ")
            print(f"   [{mark}] {t.get('capability')}: {t.get('status', 'pending')}")
    wf = g.get("workflow_result")
    if wf:
        print(f"\n{_colorify('Result', 'bold')}")
        print(f"  status: {wf.get('status')}")
        if wf.get("error"):
            print(f"  error:  {wf['error']}")


# --------------------------------------------------------------------------- REST helpers

async def _get(path: str) -> Any:
    async with httpx.AsyncClient(base_url=gateway_url(), timeout=30) as client:
        return await client.get(path)


async def _post(path: str, json_body: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=gateway_url(), timeout=30) as client:
        return await client.post(path, json=json_body or {})


def _require(resp: httpx.Response) -> dict | list:
    if resp.status_code >= 400:
        raise RuntimeError(f"gateway {resp.status_code}: {resp.text}")
    return resp.json()


# --------------------------------------------------------------------------- commands

async def cmd_run(objective: str, watch: bool, use_json: bool) -> int:
    resp = await _post("/goals", {"objective": objective})
    try:
        data = _require(resp)
    except RuntimeError as exc:
        if use_json:
            return _emit_json({"ok": False, "error": str(exc)})
        print(f"error: {exc}", file=sys.stderr)
        return 1
    goal_id = data["goal_id"]
    if use_json:
        if not watch:
            return _emit_json({"ok": True, "goal_id": goal_id, "status": data["status"]})
    else:
        print(f"{assistant_name()} submitted {_colorify(goal_id, 'cyan')} -> {_c(data['status'])}")
    if not watch:
        return 0

    spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    idx = 0
    try:
        async for raw in _ws_stream(f"{_ws_url()}/goals/ws"):
            msg = json.loads(raw)
            if msg["type"] != "snapshot":
                if msg["type"] == "done":
                    break
                continue
            g = next((x for x in msg["goals"] if x["goal_id"] == goal_id), None)
            if g is None:
                continue
            if use_json:
                _emit_json({"goal_id": goal_id, "status": g["status"], "progress": g.get("progress")})
            else:
                frames = f"\r  {spinner[idx % len(spinner)]} {g['status']} " \
                         f"({g.get('progress', {}).get('percent', 0)}%)  {g['objective'][:40]}"
                print(frames, end="", flush=True)
                idx += 1
            if g["status"] in TERMINAL:
                if not use_json:
                    print()
                    _print_goal_detail(g)
                break
    except (KeyboardInterrupt, asyncio.CancelledError):
        if not use_json:
            print(f"\n{_colorify('interrupted', 'yellow')} — goal {goal_id} left running")
        return 130
    return 0


async def _ws_stream(url: str, *, max_retries: int = 20):
    """Yield raw WebSocket messages with automatic reconnect + backoff.

    If the gateway drops the connection (restart, transient network blip), the
    stream reconnects transparently up to ``max_retries`` times with capped
    exponential backoff. Keyboard interrupt always propagates.
    """
    import asyncio as _asyncio

    attempt = 0
    while True:
        try:
            async with websockets.connect(url) as ws:
                attempt = 0  # reset backoff after a clean connection
                async for raw in ws:
                    yield raw
                return  # server closed cleanly (e.g. "done" frame handled by caller)
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        except Exception:  # transient disconnect — reconnect with backoff
            attempt += 1
            if attempt > max_retries:
                raise
            await _asyncio.sleep(min(2 ** attempt, 30))


async def cmd_goals(watch: bool, use_json: bool) -> int:
    if watch:
        return await _watch(use_json)
    resp = await _get("/goals")
    goals = _require(resp)
    if use_json:
        return _emit_json({"goals": goals, "count": len(goals)})
    print(f"{len(goals)} goal(s):")
    for g in goals:
        _print_goal_row(g)
    return 0


async def _watch(use_json: bool) -> int:
    try:
        async for raw in _ws_stream(f"{_ws_url()}/goals/ws"):
            msg = json.loads(raw)
            if msg["type"] == "snapshot":
                if use_json:
                    _emit_json({"goals": msg["goals"]})
                else:
                    print("\033[2J\033[H", end="", flush=True)
                    print(f"{_colorify('Live — goals', 'bold')} ({len(msg['goals'])})", flush=True)
                    for g in msg["goals"]:
                        _print_goal_row(g)
            elif msg["type"] == "done":
                break
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    return 0


async def cmd_goal(goal_id: str, use_json: bool) -> int:
    resp = await _get(f"/goals/{goal_id}")
    if resp.status_code == 404:
        if use_json:
            return _emit_json({"ok": False, "error": f"unknown goal: {goal_id}"})
        print(f"unknown goal: {goal_id}", file=sys.stderr)
        return 1
    g = resp.json()
    if use_json:
        return _emit_json(g)
    _print_goal_detail(g)
    return 0


async def cmd_status(goal_id: str | None, use_json: bool) -> int:
    if goal_id:
        return await cmd_goal(goal_id, use_json)
    resp = await _get("/goals")
    goals = _require(resp)
    if use_json:
        return _emit_json({"goals": goals, "count": len(goals)})
    print(f"{len(goals)} goal(s):")
    for g in goals:
        _print_goal_row(g)
    return 0


async def cmd_logs(goal_id: str | None, use_json: bool) -> int:
    if goal_id:
        resp = await _get(f"/goals/{goal_id}")
        if resp.status_code == 404:
            if use_json:
                return _emit_json({"ok": False, "error": f"unknown goal: {goal_id}"})
            print(f"unknown goal: {goal_id}", file=sys.stderr)
            return 1
        events = resp.json().get("events", [])
    else:
        goals = _require(await _get("/goals"))
        events = []
        for g in goals:
            for e in g.get("events", []):
                e = dict(e)
                e["goal_id"] = g["goal_id"]
                events.append(e)
    if use_json:
        return _emit_json({"events": events, "count": len(events)})
    for e in events:
        ts = e.get("ts", "")
        kind = e.get("type", e.get("event", "event"))
        gid = str(e.get("goal_id", ""))[:18]
        detail = e.get("detail") or e.get("message") or ""
        print(f"  {ts:<12} {_colorify(gid, 'cyan'):<20} {_colorify(kind, 'bold'):<14} {detail}")
    if not events:
        print("  (no events)")
    return 0


async def _action(verb: str, goal_id: str, use_json: bool) -> int:
    # Map CLI verbs to gateway actions.
    if verb == "retry":
        # A retry re-runs a *failed* goal: resume if paused/approval, else
        # submit a fresh goal with the same objective (API-compatible).
        resp = await _get(f"/goals/{goal_id}")
        if resp.status_code == 404:
            if use_json:
                return _emit_json({"ok": False, "error": f"unknown goal: {goal_id}"})
            print(f"unknown goal: {goal_id}", file=sys.stderr)
            return 1
        g = resp.json()
        if g["status"] in TERMINAL and g["status"] != "failed":
            if use_json:
                return _emit_json({"ok": False, "error": f"goal {goal_id} is {g['status']}, cannot retry"})
            print(f"goal {goal_id} is {g['status']}; nothing to retry", file=sys.stderr)
            return 1
        if g["status"] == "failed":
            resp2 = await _post("/goals", {"objective": g.get("objective", "")})
            data = _require(resp2)
            if use_json:
                return _emit_json({"ok": True, "goal_id": data["goal_id"], "action": "retry", "status": data["status"]})
            print(f"{assistant_name()} retried {_colorify(goal_id, 'cyan')} as new goal {_colorify(data['goal_id'], 'cyan')}")
            return 0
        # paused / waiting_approval -> resume
        resp2 = await _post(f"/goals/{goal_id}/resume")
    else:
        resp2 = await _post(f"/goals/{goal_id}/{verb}")
    try:
        data = _require(resp2)
    except RuntimeError as exc:
        if use_json:
            return _emit_json({"ok": False, "error": str(exc)})
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if use_json:
        return _emit_json({"ok": True, "goal_id": data.get("goal_id"), "status": data.get("status")})
    print(f"{verb} {_colorify(goal_id, 'cyan')} -> {_c(data.get('status', 'unknown'))}")
    return 0


async def cmd_version(use_json: bool) -> int:
    payload = {
        "assistant": assistant_name(),
        "client": "aios-cli",
        "version": __version__,
        "gateway": gateway_url(),
    }
    if use_json:
        return _emit_json(payload)
    print(f"{_colorify(assistant_name(), 'bold')} CLI  v{__version__}")
    print(f"gateway: {gateway_url()}")
    return 0


async def cmd_doctor(use_json: bool) -> int:
    checks: list[dict[str, Any]] = []
    reachable = False
    try:
        resp = await _get("/health")
        reachable = resp.status_code == 200
        checks.append({"check": "gateway reachable", "ok": reachable, "detail": f"HTTP {resp.status_code}"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"check": "gateway reachable", "ok": False, "detail": str(exc)[:80]})
    try:
        resp = await _get("/goals")
        ok = resp.status_code < 400
        checks.append({"check": "goals API", "ok": ok, "detail": f"{len(resp.json())} goals tracked"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"check": "goals API", "ok": False, "detail": str(exc)[:80]})
    ws_ok = False
    try:
        async for raw in _ws_stream(f"{_ws_url()}/goals/ws", max_retries=3):
            json.loads(raw)  # first snapshot frame
            ws_ok = True
            break
        checks.append({"check": "global WS stream", "ok": ws_ok, "detail": "connected"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"check": "global WS stream", "ok": False, "detail": str(exc)[:80]})
    all_ok = all(c["ok"] for c in checks)
    if use_json:
        return _emit_json({"ok": all_ok, "checks": checks})
    print(f"{_colorify('Doctor', 'bold')} — {assistant_name()} CLI")
    for c in checks:
        mark = _colorify("✓", "green") if c["ok"] else _colorify("✗", "red")
        print(f"  {mark} {c['check']:<20} {c['detail']}")
    print(_colorify("all systems go" if all_ok else "issues detected", "green" if all_ok else "red"))
    return 0 if all_ok else 1


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    name = assistant_name().lower()
    parser = argparse.ArgumentParser(
        prog=name,
        description=f"{assistant_name()} CLI — autonomous goal control surface",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--gateway", default=None, help="Gateway URL (overrides AIOS_GATEWAY_URL)")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Submit an objective and follow it")
    p_run.add_argument("objective", help="What the assistant should do")
    p_run.add_argument("--watch", action="store_true", help="Follow to completion (spinner)")

    p_goals = sub.add_parser("goals", help="List tracked goals")
    p_goals.add_argument("--watch", action="store_true", help="Alias for `watch`")

    p_goal = sub.add_parser("goal", help="Show one goal in detail")
    p_goal.add_argument("goal_id")

    p_status = sub.add_parser("status", help="Show goal status (all or one)")
    p_status.add_argument("goal_id", nargs="?", default=None)

    p_logs = sub.add_parser("logs", help="Show goal lifecycle events")
    p_logs.add_argument("goal_id", nargs="?", default=None)

    sub.add_parser("watch", help="Live-stream every goal from the global WS")

    for verb, h in (
        ("pause", "Pause a running goal"),
        ("resume", "Resume a paused / waiting-approval goal"),
        ("cancel", "Cancel a goal"),
        ("retry", "Retry a failed goal"),
    ):
        pp = sub.add_parser(verb, help=h)
        pp.add_argument("goal_id")

    sub.add_parser("version", help="Print client + assistant version")
    sub.add_parser("doctor", help="Check connectivity to the gateway")

    # Shell completion helpers (argparse does not generate these natively).
    comp = sub.add_parser("completion", help="Print shell completion script")
    comp.add_argument("shell", choices=["bash", "zsh", "fish"], help="Target shell")
    return parser


_COMPLETION = {
    "bash": '_aios_completions() {{\n    local cur="${{COMP_WORDS[COMP_CWORD]}}"\n    local cmds="run goals goal status logs watch pause resume cancel retry version doctor completion"\n    COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )\n    return 0\n}}\ncomplete -F _aios_completions {name}\n',
    "zsh": '#compdef {name}\n_{name}() {{\n    local -a cmds\n    cmds=(run goals goal status logs watch pause resume cancel retry version doctor completion)\n    _describe "command" cmds\n}}\ncompdef _{name} {name}\n',
    "fish": 'complete -c {name} -f\nfor c in run goals goal status logs watch pause resume cancel retry version doctor completion\n    complete -c {name} -a $c\nend\n',
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gateway:
        os.environ["AIOS_GATEWAY_URL"] = args.gateway

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "completion":
        name = assistant_name().lower()
        sys.stdout.write(_COMPLETION[args.shell].format(name=name))
        return 0
    if args.command == "version":
        return asyncio.run(cmd_version(args.json))
    if args.command == "doctor":
        return asyncio.run(cmd_doctor(args.json))
    if args.command == "run":
        return asyncio.run(cmd_run(args.objective, args.watch, args.json))
    if args.command == "goals":
        return asyncio.run(cmd_goals(args.watch, args.json))
    if args.command == "goal":
        return asyncio.run(cmd_goal(args.goal_id, args.json))
    if args.command == "status":
        return asyncio.run(cmd_status(args.goal_id, args.json))
    if args.command == "logs":
        return asyncio.run(cmd_logs(args.goal_id, args.json))
    if args.command == "watch":
        return asyncio.run(_watch(args.json))
    if args.command in {"pause", "resume", "cancel", "retry"}:
        return asyncio.run(_action(args.command, args.goal_id, args.json))

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
