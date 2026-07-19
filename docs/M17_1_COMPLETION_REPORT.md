# M17.1: Developer Mode Integration Pass

**Date:** 2026-07-20
**Version:** v0.17.0
**Status:** COMPLETE — 241 tests passing (M16: 144 + M17: 97)

## Summary

Integration pass that wires the M17 Developer Mode backend modules (WorkforceManager, CLIController, ReviewPipeline) to the gateway API and frontend. Adds 15 FastAPI endpoints, a full API client, and fixes backward-compatible shortcuts.

## Changes

### Backend — Gateway Endpoints (15 new)

| Category | Endpoint | Method |
|----------|----------|--------|
| Workforce | `/workforce/workers` | GET |
| Workforce | `/workforce/workers/{id}` | GET |
| Workforce | `/workforce/capability/{cap}` | GET |
| Workforce | `/workforce/assign` | POST |
| Workforce | `/workforce/complete` | POST |
| Workforce | `/workforce/fail` | POST |
| Workforce | `/workforce/state` | GET |
| CLI | `/cli/active` | GET |
| CLI | `/cli/spawn` | POST |
| Review | `/review/active` | GET |
| Review | `/review/create` | POST |
| Review | `/review/{id}/verdict` | POST |
| Review | `/review/state` | GET |

In-memory stores with 8 default workers: architect, backend, frontend, qa, devops, researcher, designer, reviewer.

### Frontend — API Client

- `apps/web/src/lib/api.ts` — Full fetch-based API client with `workforce.*`, `cli.*`, `reviews.*` namespaces
- Matches gateway endpoint contract exactly

### Frontend — Integration Fixes

- `apps/web/src/desktop/layout/AppShell.tsx` — Added `toggleDevMode` alias for ⌘⇧D shortcut backward compatibility
- `apps/web/src/desktop/workspaces/registry.tsx` — Fixed invalid `export function get workspaces()` syntax → `export const workspaces`

### Infrastructure

- `.gitignore` — Added `!apps/web/src/lib/` negation (Python `lib/` pattern was catching web app's API module)

## Commits

```
1015c43 feat(frontend): implement DevMode API client and fix integration
4cd6d6b feat(gateway): add M17 workforce, CLI, and review endpoints
06d47a0 chore(git): un-ignore apps/web/src/lib for API client
```

## Test Results

```
M16 features: 144 passed
M17 devmode:  97 passed
Total:        241 passed
```

## Known Issues

- Next.js 16.2.10 Turbopack build broken by `~/package-lock.json` confusing workspace root detection (pre-existing, unrelated to M17)
- 58 test collection errors from missing optional packages (playwright, torch, etc.)

## Next Steps

- M17.2: Developer Mode workspaces (Workforce, Repositories, Consoles, Reviews as separate workspace entries)
- M18: Mission Control — goal-centric default workspace
- Turbopack workspace root resolution fix
