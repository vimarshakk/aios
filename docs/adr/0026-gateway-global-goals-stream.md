# ADR-0026: Gateway Global Goals Event Stream

**Status:** Accepted
**Date:** 2025-07-18
**Supersedes:** — (complements ADR-0022 Native-first resolution, M5.1 gateway goals)

## Context

The gateway already exposes the full Priority-1 external-control surface for the
Supervisor (M5.1):

- `POST /goals`, `GET /goals`, `GET /goals/{id}`
- `POST /goals/{id}/pause|resume|cancel`
- `WS /goals/{id}/events` — a per-goal progress stream

A dashboard / multi-agent viewer, however, needs a **single global stream** that
surfaces *all* goals as they change — not one WebSocket per goal. Without it,
a UI must poll `GET /goals` on a timer, which is wasteful and laggy.

## Decision

Add `WS /goals/ws` to `services/gateway/src/aios/gateway/main.py`. It is a thin
adapter over the shared `Supervisor` (via `get_supervisor()`) that:

1. Sends an initial `{"type": "snapshot", "goals": [...]}` frame immediately so
   a freshly-connected client sees current state.
2. Polls `Supervisor.list_goals()` every 250ms and re-emits a `snapshot` frame
   only when a cheap fingerprint (per-goal `status` + `len(events)`) changes —
   avoiding redundant traffic.
3. When **every** tracked goal is in a terminal state (`completed` / `failed` /
   `cancelled`), emits a `{"type": "done"}` frame and closes the socket, so
   followers (dashboards, integration tests) exit cleanly instead of polling
   forever.

The payload shape reuses `Goal.to_dict()` (already carrying `task_graph`,
`events`, and `workflow_result`), so the global stream is wire-compatible with
the per-goal `WS /goals/{id}/events` and the `GET /goals` REST response.

## Consequences

- **Positive:** One connection gives a live, multi-goal view; trivial to consume
  from a browser (`WebSocket`) or a CLI (`aios goals` watcher). No new data
  model — reuses the existing `Goal.to_dict()` contract.
- **Positive:** `done` frame makes the stream self-terminating for bounded
  sessions; long-lived observers can simply reconnect.
- **Negative:** Polling at 250ms is coarse (≤250ms event latency). Acceptable
  for a control/dashboard surface; a future push model (subscribe to an event
  bus) can replace the poll loop without changing the wire protocol.
- **Negative:** Snapshot frames can be large for goals with big `task_graph`s;
  clients should filter. Out of scope for this release.

## Alternatives Considered

- **Event-bus push:** More precise, but requires the Supervisor to publish to a
  bus the gateway subscribes to. Adds infrastructure for marginal benefit at
  this stage. Deferred.
- **SSE instead of WS:** `GET /goals/stream` (SSE) is a natural fit for
  one-way server→client. Chosen WS instead to stay consistent with the existing
  `WS /goals/{id}/events` and to allow future client→server commands (e.g.
  subscribe to a subset of goal IDs) without a protocol switch.

## Compliance

- FROZEN interfaces (`Skill*`, `aios.agents.permissions.*`) untouched.
- The endpoint adapts the existing `Supervisor` public API (`list_goals`);
  no new supervisor methods introduced.

## Tests

`tests/test_gateway_goals_ws.py` — route registration + offline (fake-platform)
assertion that the stream emits a snapshot containing a seeded goal and a
terminal `done` frame. Suite: **1161 passed, 55 skipped**. Ruff clean.
