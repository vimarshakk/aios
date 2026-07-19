# AIOS CLI Reference

The `aios` command is a thin client over the AIOS gateway's REST + WebSocket
API. It requires a running gateway (`AIOS_GATEWAY_URL`, default
`http://localhost:8080`).

> **Rebranding:** set `AIOS_ASSISTANT_NAME` (default `AIOS`) to rename the
> assistant in all CLI output. No core code references the name directly.

## Global flags

| Flag | Description |
|---|---|
| `--json` | Emit machine-readable JSON for the command |
| `--gateway <url>` | Override `AIOS_GATEWAY_URL` for this invocation |

## Commands

### `aios "<objective>" [--watch]`
Submit a goal and (with `--watch`) follow it to completion with a spinner.
The watch stream ends when the goal reaches a terminal state.

### `aios goals [--watch]`
List all tracked goals as a table (`goal_id`, status, progress, objective).
`--watch` live-streams every goal from `WS /goals/ws`.

### `aios goal <id>`
Show one goal in full: objective, status, progress, task list (with per-task
status), and the `workflow_result`.

### `aios status [id]`
Summary of all goals, or a single goal if `id` is given.

### `aios logs [id]`
Print the lifecycle `events` (`ts`, `type`, `detail`) for one goal, or for all
goals when `id` is omitted.

### `aios watch`
Live-stream every goal from the global `WS /goals/ws`, redrawing the screen on
each snapshot. Exits when all goals are terminal (receives the `done` frame).

### `aios pause <id>` / `resume <id>` / `cancel <id>`
Map directly to the gateway's `POST /goals/{id}/{pause,resume,cancel}` actions.
`resume` only applies to `paused` / `waiting_approval` goals.

### `aios retry <id>`
Retry a **failed** goal by submitting a fresh goal with the same objective
(API-compatible; `resume` cannot restart a `failed` goal).

### `aios version`
Print client name, assistant name, CLI version, and gateway URL.

### `aios doctor`
Connectivity self-check: gateway reachable (`/health`), goals API (`/goals`),
and the global WebSocket stream (`/goals/ws`). Exits non-zero if any fail.

### `aios completion <bash|zsh|fish>`
Emit a shell completion script. Example:

```bash
aios completion bash >> ~/.bashrc
aios completion zsh  >> ~/.zshrc
aios completion fish  > ~/.config/fish/completions/aios.fish
```

## Output conventions

- **Tables** by default; add `--json` for structured output (stable
  `Goal.to_dict` shape).
- **Colors** are emitted only when stdout is a TTY; redirected/piped output is
  plain text.
- **`run --watch`** uses a Unicode spinner; `Ctrl-C` leaves the goal running
  and returns exit code `130`.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `AIOS_GATEWAY_URL` | `http://localhost:8080` | Gateway base URL |
| `AIOS_ASSISTANT_NAME` | `AIOS` | Assistant display name |
