"""AIOS Supervisor service entrypoint.

This is a thin runnable surface for the Supervisor. It wires a
:class:`DeveloperPlatform` and exposes a simple programmatic loop plus an
optional HTTP server (mirroring the gateway's ``run()`` contract). The M5
AIOS Desktop experience is expected to drive the Supervisor over the
gateway's existing transport; this entrypoint keeps the service self-runnable
for local dev and smoke tests.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from aios.platform import DeveloperPlatform

from .briefing import BriefingConfig, BriefingEngine
from .daemon import Daemon, DaemonConfig
from .supervisor import Supervisor

logger = logging.getLogger("aios.supervisor.main")


def build_supervisor() -> Supervisor:
    """Construct a Supervisor backed by a default DeveloperPlatform."""
    platform = DeveloperPlatform()
    platform.bootstrap()
    return Supervisor(platform)


async def _demo(objective: str) -> None:
    supervisor = build_supervisor()
    goal = await supervisor.submit(objective)
    # Wait for the background execution to settle (best-effort demo).
    for _ in range(50):
        await asyncio.sleep(0.1)
        g = supervisor.get_goal(goal.goal_id)
        if g is not None and g.is_terminal:
            break
    logger.info("Goal %s -> %s", goal.goal_id, goal.status.value)
    logger.info("Progress: %s", goal.progress())


def run() -> None:
    """Console-script entrypoint (aios-supervisor / aios)."""
    parser = argparse.ArgumentParser(prog="aios-supervisor")
    parser.add_argument(
        "objective",
        nargs="?",
        default=None,
        help="Objective for the supervisor to execute (omitted => interactive).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging."
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.objective:
        asyncio.run(_demo(args.objective))
    else:
        asyncio.run(_aios_repl())


def run_daemon() -> None:
    """Console-script entrypoint (aiosd) — long-running AIOS daemon (M5.3)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    platform = DeveloperPlatform()
    platform.bootstrap()
    briefing = BriefingEngine(platform=platform, config=BriefingConfig())
    daemon = Daemon(platform, DaemonConfig(briefing=briefing))
    daemon.run_forever()


async def _aios_repl() -> None:
    """Interactive AIOS REPL driving the Supervisor locally."""
    supervisor = build_supervisor()
    print("AIOS ready. Type an objective, or 'quit' to exit.")
    print("Example: 'Summarize today\\'s work'  /  'Clean Downloads'")
    while True:
        try:
            line = input("\nAIOS> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not line or line.lower() in {"quit", "exit"}:
            break
        goal = await supervisor.submit(line)
        print(f"  goal {goal.goal_id} -> {goal.status.value}")
        while not goal.is_terminal:
            await asyncio.sleep(0.25)
        prog = goal.progress()
        print(f"  done: {goal.status.value} ({prog['completed']}/{prog['total_steps']})")
        for step in goal.steps:
            mark = "+" if step.status.value == "success" else "!"
            print(f"   [{mark}] {step.skill}: {step.status.value}")


if __name__ == "__main__":
    run()
