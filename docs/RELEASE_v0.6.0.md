# AIOS v0.6.0 — Native-First Core

**Release date:** 2025-07-18
**Type:** Minor (offline-first product capability)
**Supersedes:** v0.5.0 (Supervisor + Composio, ADR-0021)

## Summary

AIOS now runs **completely offline** with AIOS-native capabilities. External
integrations (Composio, GitHub, Notion, Gmail, …) are optional providers the
system may prefer when connected — never dependencies. This delivers the core
M5 product promise: an AIOS-native experience that does not require the
cloud or any third party to be usable.

## What's New

### Capability Resolver (`packages/platform`)
- `CapabilityResolver` with native-first ranking: native skill > available
  optional provider > unavailable > none.
- `DeveloperPlatform.resolve(capability)` and `register_provider(...)`.
- `bootstrap()` registers the native desktop skills as preferred providers.

### Native Desktop Skills (`packages/skills/native`)
- `terminal`, `filesystem`, `git`, `docker`, `notes`, `notify` — all offline,
  AIOS-owned implementations bound to catalog capabilities + frozen permissions.
- `register_native_skills(registry, resolver)` bootstraps them.

### Supervisor API on Gateway (M5.1)
- `POST /goals`, `GET /goals`, `GET /goals/{id}`, `POST /goals/{id}/pause`,
  `POST /goals/{id}/resume`, `POST /goals/{id}/cancel`, `WS /goals/{id}/events`.

### AIOS CLI (M5.2)
- `aios` interactive REPL (`aios-supervisor` console script) submits objectives
  to the Supervisor and streams progress.

## Quality

- Lint: `ruff check packages/ services/` — clean (new code).
- Tests: **1141 passed, 55 skipped** (full suite, no regressions).
- New tests: `test_capability_resolver.py` (5), `test_native_skills.py` (5),
  `test_supervisor_api.py` (2).
- Frozen interfaces (`Permission`, `PermissionChecker`, `PermissionSet`)
  untouched.

## Upgrade Notes

- No schema/migration changes.
- Native skills require the corresponding local binaries only when invoked
  (e.g., `docker`, `git`). Missing binaries fail the single skill gracefully —
  the rest of AIOS is unaffected.
- To enable external ecosystems, connect integrations as before (ADR-0021); the
  resolver will then prefer them for capabilities the native skills don't own.
