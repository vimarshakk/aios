# AIOS v0.6.5 — Gateway Global Goals Event Stream (Priority 1)

**Release date:** 2025-07-18
**Type:** Minor (external-control surface completion)
**Supersedes:** v0.6.4 (M6.1 parallel/retry/reflection, ADR-0025)

## Summary

Completes **Priority 1** of the external-control roadmap: a single global
WebSocket that streams the state of *all* Supervisor goals. The gateway already
shipped the per-goal REST control surface and a per-goal event socket in M5.1
(`POST /goals`, `GET /goals`, `GET /goals/{id}`, pause/resume/cancel, and
`WS /goals/{id}/events`). This release adds `WS /goals/ws` so a dashboard or
CLI viewer can watch every goal from one connection.

The stream:

- Sends an initial `{"type": "snapshot", "goals": [...]}` frame on connect.
- Re-emits a `snapshot` whenever any goal's `status` or event count changes
  (250ms poll, cheap fingerprint to avoid redundant frames).
- Emits `{"type": "done"}` and closes once **all** tracked goals are terminal —
  so bounded observers exit cleanly instead of polling forever.

Payloads reuse `Goal.to_dict()` (carrying `task_graph`, `events`,
`workflow_result`), making the global stream wire-compatible with the per-goal
WebSocket and the `GET /goals` REST response.

## What Changed

- `services/gateway/src/aios/gateway/main.py`: new `WS /goals/ws`
  (`goals_stream`). `services/gateway/pyproject.toml`: added `[dependency-groups]`
  `dev = ["httpx2>=0.28"]` so the FastAPI `TestClient` WebSocket tests run
  against the newer starlette that requires `httpx2`.
- `tests/test_gateway_goals_ws.py`: new — route registration + offline
  (fake-platform) test asserting the stream emits a snapshot with a seeded goal
  and a terminal `done` frame.
- `docs/adr/0026-gateway-global-goals-stream.md`, `docs/RELEASE_v0.6.5.md`.

## Examples

```js
const ws = new WebSocket("ws://localhost:8080/goals/ws");
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === "snapshot") renderDashboard(msg.goals);
  if (msg.type === "done") ws.close(); // all goals finished
};
```

## Compliance

- FROZEN interfaces (`Skill`, `SkillManifest`, `SkillContext`, `SkillResult`,
  `SkillStatus`, `aios.agents.permissions.*`) unchanged.
- New endpoint adapts only the existing `Supervisor.list_goals()` public API;
  no new supervisor methods.
- Suite: **1161 passed, 55 skipped**. Ruff clean (`services/`, `tests/`;
  pre-existing `tests/test_browser.py` I001 excluded).

## Deferred

Priority 2 (`aios` CLI `goals`/`status`/`logs` commands consuming this stream)
and Priority 3 (semantic long-term memory). The stream is the data backbone
those commands will build on.

## Related

- ADR-0026 (this release), ADR-0022 (native-first resolution), M5.1 gateway
  goals (per-goal REST + WS).
