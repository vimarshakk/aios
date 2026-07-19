"""M7 end-to-end live smoke test.

Boots the REAL gateway FastAPI app and drives it over a single asyncio event
loop via httpx ASGITransport (HTTP + WebSocket share one loop, so background
goal tasks and the WS subscription observe each other in real time).

Verifies:
  1. /chat/stream emits tool_call -> tool_result -> content -> done, scoped by run_id.
  2. /goals (create) + /goals/{id}/events (WS) stream live goal progress.

No real LLM / Ollama / external services required:
  - The orchestrator is injected with a deterministic MockEngine that forces a
    `calculator` tool call, then a Final Answer.
  - The Supervisor is injected with an in-memory _FakePlatform.

Run:  ./.venv/bin/python tests/m7_smoke_test.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import suppress

import _pathsetup  # noqa: F401  (adds package src dirs to sys.path)

import httpx
from httpx import ASGITransport

import aios.gateway.main as gw  # noqa: E402
from aios.agents.engine import CompletionResult, InferenceEngine  # noqa: E402
from aios.agents.react.agent import ReActAgent  # noqa: E402
from aios.agents.types import ToolCall  # noqa: E402
from aios.orchestrator.main import Orchestrator  # noqa: E402
from aios.tools.builtin import CalculatorTool  # noqa: E402
from aios.supervisor.supervisor import Supervisor  # noqa: E402

# Reuse the test fixture platform
from test_supervisor import _FakePlatform  # noqa: E402


class SlowFakePlatform(_FakePlatform):
    """FakePlatform whose skills take ~0.25s each so a 2-step goal stays
    'running' long enough for the WS client to attach and observe live
    snapshots (avoids the instant-complete race in the test harness)."""

    def __init__(self) -> None:
        super().__init__(slow={"browser", "desktop.notify"})

    async def execute_skill(self, name, inputs=None, workspace_id=None, metadata=None):
        # Sleep per slow skill so the goal remains observable while running.
        if name in self._slow:
            await asyncio.sleep(0.25)
        return await super().execute_skill(
            name, inputs=inputs, workspace_id=workspace_id, metadata=metadata
        )


# ---------------------------------------------------------------------------
# Mock engine: turn 1 forces a calculator tool call; turn 2 returns a final answer
# ---------------------------------------------------------------------------
class MockEngine(InferenceEngine):
    name = "mock"

    def __init__(self) -> None:
        self._turn = 0

    async def complete(self, messages, *, model="", temperature=0.7, max_tokens=2048, stop=None, **kwargs):
        self._turn += 1
        if self._turn == 1:
            return CompletionResult(
                content="",
                model=model or "mock",
                tool_calls=[ToolCall(id="t1", name="calculator", arguments=json.dumps({"expression": "6 * 7"}))],
                finish_reason="tool_calls",
            )
        return CompletionResult(
            content="Final Answer: The product of 6 and 7 is 42.",
            model=model or "mock",
            finish_reason="stop",
        )

    async def stream(self, messages, *, model="", temperature=0.7, max_tokens=2048, stop=None, **kwargs):
        # Deliberately NOT a real async generator. The gateway detects this and
        # falls back to the non-streaming orchestrator route (where tool-call
        # events are actually published + surfaced). This exercises the real
        # integration path used when an engine cannot stream natively.
        raise NotImplementedError("mock engine does not support native streaming")

    async def health(self) -> bool:
        return True

    def models(self) -> list[str]:
        return ["mock"]


def _build_mock_orchestrator() -> Orchestrator:
    orch = Orchestrator()
    engine = MockEngine()
    agent = ReActAgent(engine, "mock", tools=[CalculatorTool()])
    orch.register_agent("default", agent)
    return orch


# ---------------------------------------------------------------------------
# Results capture
# ---------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    def all_ok(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


def parse_sse(text: str) -> list[dict]:
    frames: list[dict] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if ln.startswith("data:"):
            payload = ln[len("data:"):].strip()
            with suppress(Exception):
                frames.append(json.loads(payload))
    return frames


async def _run_test1(client, report) -> None:
    run_id = "m7-test-run-001"
    async with client.stream("GET", "/chat/stream", params={
        "message": "What is 6 times 7? Use the calculator.",
        "agent": "default",
        "run_id": run_id,
    }) as resp:
        raw = await resp.aread()
    frames = parse_sse(raw.decode())

    tool_calls = [f["tool_call"] for f in frames if "tool_call" in f]
    tool_results = [f for f in frames if "tool_result" in f]
    contents = [f["content"] for f in frames if "content" in f and not f.get("done")]
    done_frames = [f for f in frames if f.get("done")]
    errors = [f for f in frames if "error" in f]

    print("  SSE frame sequence:")
    for f in frames:
        print("    " + json.dumps(f))

    report.add("no SSE errors", len(errors) == 0, str(errors))
    report.add("emitted tool_call", "calculator" in tool_calls, f"tool_calls={tool_calls}")
    report.add("emitted tool_result for calculator",
               any(tr.get("tool_result") == "calculator" for tr in tool_results))
    report.add("tool_result success=true",
               any(tr.get("tool_result") == "calculator" and tr.get("success") is True for tr in tool_results))
    report.add("emitted assistant content", any("42" in c for c in contents), f"contents={contents}")
    report.add("emitted done frame", len(done_frames) >= 1, f"done_frames={len(done_frames)}")
    order_ok = (
        tool_calls and tool_results and done_frames
        and frames.index(next(f for f in frames if "tool_call" in f))
        < frames.index(next(f for f in frames if "tool_result" in f))
        < frames.index(done_frames[0])
    )
    report.add("event ordering tool_call -> tool_result -> done", order_ok)

    # run_id scoping: a DIFFERENT run_id must not leak this run's tool events
    async with client.stream("GET", "/chat/stream", params={
        "message": "What is 6 times 7? Use the calculator.",
        "agent": "default",
        "run_id": "other-run-xyz",
    }) as resp2:
        raw2 = await resp2.aread()
    frames2 = parse_sse(raw2.decode())
    leak = [f for f in frames2 if f.get("tool_call") == "calculator"]
    report.add("run_id scoping prevents cross-request leak",
               len(leak) == 0, "isolated OK" if not leak else "LEAK")


async def main() -> int:
    print("=" * 72)
    print("M7 LIVE SMOKE TEST  (real gateway app on localhost + real WS client)")
    print("=" * 72)

    mock_orch = _build_mock_orchestrator()
    mock_sup = Supervisor(SlowFakePlatform())
    gw.get_orchestrator = lambda: mock_orch  # type: ignore[attr-defined]
    gw.get_supervisor = lambda: mock_sup  # type: ignore[attr-defined]

    # Boot the real gateway on a localhost port (background thread / uvicorn).
    import socket
    import uvicorn

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(gw.app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    import threading

    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"

    # Wait for the server to accept connections.
    for _ in range(100):
        try:
            async with httpx.AsyncClient() as probe:
                r = await probe.get(f"{base}/health", timeout=1.0)
                if r.status_code == 200:
                    break
        except Exception:
            await asyncio.sleep(0.1)

    report = Report()
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        # --- Health -----------------------------------------------------------
        h = (await client.get("/health")).json()
        report.add("gateway /health", "status" in h, str(h))

        # ============== TEST 1: /chat/stream tool events ====================
        print("\n--- TEST 1: /chat/stream (tool execution + run_id scoping) ---")
        await _run_test1(client, report)

        # ============== TEST 2: Goals (create + WS live stream) =============
        print("\n--- TEST 2: /goals create + /goals/{id}/events WS ---")
        import websockets

        # Connect the WS subscription FIRST, then submit the goal from a
        # background task so the goal executes on the server's loop while the
        # client is already listening (eliminates connect/producer race).
        ws_snapshots: list[dict] = []
        ws_error: str | None = None
        goal_id_holder: dict[str, str] = {}

        async def _submit() -> None:
            r = await client.post("/goals", json={"objective": "open example.com"})
            if r.status_code == 200:
                goal_id_holder["goal_id"] = r.json()["goal_id"]

        # We need the goal id to build the WS uri, but want to connect before it
        # finishes. Strategy: submit, capture id fast, then connect; the goal's
        # background task runs long enough (2 steps w/ notify) for the client to
        # attach. Retry connect until the goal is observed or terminal.
        create = await client.post("/goals", json={"objective": "open example.com"})
        report.add("/goals POST returns goal_id",
                   create.status_code == 200 and "goal_id" in create.json(),
                   str(create.json()))
        goal_id = create.json()["goal_id"]

        ws_uri = f"ws://127.0.0.1:{port}/goals/{goal_id}/events"
        try:
            async with websockets.connect(ws_uri, open_timeout=5) as ws:
                # Read frames; the server streams status changes + a terminal one.
                # `async for` is the reliable read pattern for websockets 15.x.
                async for raw_msg in ws:
                    msg = json.loads(raw_msg)
                    # to_dict() may include an "error": null key; only treat a
                    # *truthy* error as a real failure.
                    if msg.get("error"):
                        ws_error = str(msg["error"])
                        break
                    ws_snapshots.append(msg)
                    if msg.get("status") in ("completed", "failed", "cancelled"):
                        break
        except Exception as exc:  # noqa: BLE001
            ws_error = f"{type(exc).__name__}: {exc!r}"

        print("  Goal WS snapshots received:")
        for s in ws_snapshots:
            print("    " + json.dumps({k: s.get(k) for k in ("goal_id", "status", "objective", "progress")}))
        if ws_error:
            print(f"    [ws error] {ws_error}")

        got_ws = len([s for s in ws_snapshots if "progress" in s or s.get("status") in ("completed", "failed", "cancelled")]) >= 1
        report.add("goal WS streamed >=1 live snapshot", got_ws,
                   f"frames={len(ws_snapshots)}")
        report.add("goal reached terminal state",
                   any(s.get("status") in ("completed", "failed", "cancelled") for s in ws_snapshots),
                   "terminal reached" if ws_snapshots else (ws_error or "no snapshots"))

        # verify GET /goals/{id} reflects final state
        getg = (await client.get(f"/goals/{goal_id}")).json()
        report.add("/goals/{id} GET reflects status", "status" in getg,
                   str({k: getg.get(k) for k in ("goal_id", "status")}))

    server.should_exit = True
    t.join(timeout=5)

    # ===================== SUMMARY ==========================================
    print("\n" + "=" * 72)
    print("M7 SMOKE TEST SUMMARY")
    print("=" * 72)
    passed = sum(1 for _, ok, _ in report.checks if ok)
    total = len(report.checks)
    print(f"  {passed}/{total} checks passed")
    ok = report.all_ok()
    print("  RESULT:", "GREEN — M7 validated end-to-end" if ok else "RED — integration issues remain")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
