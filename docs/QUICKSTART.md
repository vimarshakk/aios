# Quick Start

Get the AIOS autonomous assistant running locally in five minutes.

## Prerequisites

- Python **3.12**
- [`uv`](https://docs.astral.sh/uv/) (package/project manager)
- *(optional)* Playwright + Chromium for browser workflows
- *(optional)* an LLM provider key for summarise/research workflows

## 1. Clone & sync

```bash
git clone <repo> aios && cd aios
uv sync --all-packages -p 3.12
```

## 2. Start the gateway

The gateway exposes the REST + WebSocket API the CLI talks to.

```bash
# default port 8080; override with AIOS_GATEWAY_PORT
uv run aios-gateway
# or pick a port:
AIOS_GATEWAY_PORT=8137 uv run aios-gateway
```

Verify it is healthy:

```bash
curl -s http://localhost:8080/health
# => {"status":"ok", ...}
```

## 3. Talk to it with the CLI

```bash
export AIOS_GATEWAY_URL=http://localhost:8080   # or: aios --gateway <url>

# Submit a goal and watch it run
aios "save a note titled Ideas with body Ship v0.7.0 this week" --watch

# Inspect goals
aios goals
aios goal <goal-id>
aios logs <goal-id>

# Live stream of everything
aios watch
```

## 4. Self-check

```bash
aios doctor
```

Checks gateway reachability, the goals API, and the WebSocket stream. Exits
non-zero if any check fails.

## 5. Rename the assistant (optional)

```bash
AIOS_ASSISTANT_NAME="Nova" aios version
```

## What just happened?

`aios` sent your objective to the gateway → the **supervisor** decomposed it
with the **autonomous planner** into a task graph (e.g. `notes.write` →
`desktop.notify`) → the **native executor** ran each step via a native skill →
results streamed back over REST/WebSocket. See [ARCHITECTURE.md](ARCHITECTURE.md)
and [EXAMPLES.md](EXAMPLES.md).

## Next

- [Examples](EXAMPLES.md) — copy-paste workflows
- [Troubleshooting](TROUBLESHOOTING.md) — when something doesn't run
- [CLI Reference](CLI_REFERENCE.md) — every command/flag
