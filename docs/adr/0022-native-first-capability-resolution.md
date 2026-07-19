# ADR-0022: Native-First Capability Resolution

**Date:** 2025-07-18
**Status:** Accepted
**Deciders:** Core team

## Context

M5 is the core AIOS product experience. The defining requirement (per the
product owner) is: **AIOS must function completely offline with AIOS-native
capabilities.** External services — Composio, GitHub API, Notion, Gmail, Slack,
Linear — are *optional providers*, never dependencies.

Concretely, with no internet and no integrations connected, a user must be able
to say:

> Open Terminal. Find all Python projects. Run tests.
> Explain failures. Clean Downloads. Summarize today's work. Start coding.

This requires a single architectural rule: **every capability must have an
AIOS-native implementation where feasible.** When an optional provider (Composio
/ MCP / third-party API) is connected, the system may *prefer* it, but never
*require* it.

## Decision

### Capability Resolver (`packages/platform`, `CapabilityResolver`)
A new platform component ranks providers for a logical capability
(`notes.write`, `email.send`, `filesystem.read`, …):

1. **AIOS-native skill** — always preferred, treated as offline-capable.
2. **Optional provider that is currently available** (connected) — used only
   when no native skill exists.
3. **Registered-but-unavailable** — surfaced with a clear "connect the
   integration to enable" message.
4. **No provider** — "No provider registered."

The resolver is additive/idempotent and consults the skill registry for native
skill existence. It does not invent implementations.

`DeveloperPlatform` gains `resolve(capability)` and `register_provider(...)`
passthroughs; `bootstrap()` registers the native desktop skills as the preferred
providers.

### Native Desktop Skills (`packages/skills/native`)
A new skill module implementing Layer-2 capabilities with AIOS-owned, offline
code, each gated by the correct catalog capability + frozen permission:

| Skill | Capability | Mechanism |
|-------|-----------|-----------|
| `terminal` | `terminal.exec` | local `bash -c` subprocess |
| `filesystem` | `filesystem.read/.write/.search` | local FS |
| `git` | `git.*` | local `git` |
| `docker` | `docker.*` | local `docker` |
| `notes` | `notes.write/.read` | local markdown notebook (`~/.aios/notes`) |
| `notify` | `desktop.notify` | `aios.desktop.notifications` |
| `browser` | `browser.open/.search/.screenshot/.extract_text/.click/.type/.automate` | local `aios.browser.BrowserSession` (Playwright/Chromium) with domain allowlist + SSRF guard + audit log |

These are the offline-first providers for their capabilities; Composio/Notion/
Gmail remain optional providers the resolver can prefer when connected.

### Supervisor as the single execution interface (M5.1)
The gateway exposes goal management over the shared `Supervisor`:
`POST /goals`, `GET /goals`, `GET /goals/{id}`, `POST /goals/{id}/{pause,
resume,cancel}`, and `WS /goals/{id}/events`. External integrations are never
on the critical path — a goal runs entirely on native skills offline.

### AIOS CLI (M5.2)
`aios` (console script in `services/supervisor`) is an interactive REPL that
submits objectives to the Supervisor and prints live progress. `aios-supervisor
<objective>` runs a single goal.

## Consequences

- AIOS works with **zero integrations**: all example goals run via native
  skills (terminal, filesystem, git, docker, notes, notify).
- External ecosystems plug into the *same* capability graph via the resolver;
  the Supervisor is provider-agnostic.
- No frozen interfaces (`Permission`, `PermissionChecker`, `PermissionSet`)
  were modified; native skills declare the existing catalog capabilities and
  frozen permissions.
- M5.3 (daemon) and M5.5 (proactive briefings) build on this resolver + native
  skills foundation in a later pass.

## Alternatives considered

- **Build first-party SaaS connectors** (GitHub/Notion/…): rejected — duplicates
  Composio and violates the offline-first rule. External apps are optional
  providers only.
- **Require LLM at plan time**: deferred — M5.1–M5.2 keep planning deterministic
  (skill-name/description matching) so goals run with no model configured.
