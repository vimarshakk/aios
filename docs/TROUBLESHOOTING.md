# Troubleshooting

## The CLI can't reach the gateway

```bash
aios doctor
```

- **`/health` unreachable** — the gateway isn't running, or `AIOS_GATEWAY_URL`
  points at the wrong host/port. Start it with `uv run aios-gateway` and check
  the URL/port. The gateway reads `AIOS_GATEWAY_PORT` (default `8080`).
- **WebSocket check fails but REST works** — the gateway process may be behind a
  proxy that strips WS upgrades; connect directly.

## A goal shows `0/N completed` but the work happened

This was a **v0.7.0 bug** (step records weren't synced). Fixed in v0.7.0 — if
you still see it, upgrade. Verified: `aios goal <id>` now shows each step as
`success`/`failed` with attempts.

## A note was saved as "Captured goal" with the raw text as the body

v0.7.0 fixed note parsing. Use an explicit phrasing to be safe:

```bash
aios "save a note titled <Title> with body <Body>"
```

Avoid ambiguous phrasing like "remember that …" which the offline planner
captures literally.

## `llm.summarize` / research steps fail with "no available provider"

No LLM provider is configured (no API key / `litellm`/`openai`/`anthropic`
credentials). Browser/summarise workflows need a provider. Set the relevant
provider env vars and restart the gateway. The goal ends `failed` with a clear
error — this is expected, not a crash.

## Browser workflows don't open a page

Playwright/Chromium isn't installed. The `browser.*` step fails gracefully.
Install Playwright (`uv run playwright install chromium`) for web workflows.

## A step is stuck `pending` / the goal never reaches a terminal state

- Check `aios logs <id>` for the lifecycle events.
- A dependency that failed blocks its dependents (they become `failed`).
- If the executor raised unexpectedly it is caught and the goal ends `failed`
  with the error attached — never silently hung.

## Permission denied for a native skill

Native skills declare the permissions they need (`FILESYSTEM_WRITE`,
`FILESYSTEM_READ`, `PROCESS_EXEC`, `DESKTOP_NOTIFY`). The offline OS grants
these at bootstrap. If you see a permission error, the platform wasn't
bootstrapped with `DeveloperPlatform().bootstrap()`.

## Docker: container exits immediately

- Check the log: `docker logs <container>`. The image runs the `aios-gateway`
  console script (not `python -m aios.gateway.main`).
- Ensure port `8080` is free, or set `AIOS_GATEWAY_PORT`.
- The health check hits `/health`; a failing health check restarts the container.

## Getting help

```bash
aios --help
aios <command> --help
```
