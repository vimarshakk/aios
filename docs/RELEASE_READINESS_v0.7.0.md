# Release Readiness: v0.7.0

## Status: READY

## Validation

| Check | Result |
|-------|--------|
| Ruff lint (`packages/ services/ tests/`) | Clean (0 warnings, pre-existing `tests/test_browser.py` I001 excluded) |
| Test suite | 1195 passed, 55 skipped (network-gated) |
| Build (`uv sync --all-packages -p 3.12`) | Clean |
| Frozen interfaces | Untouched (`Permission`, `PermissionChecker`, `PermissionSet`, `Skill*`) |
| Branding | All source code, docs, and tests reference AIOS (no legacy product names) |
| Daemon persistence | Verified: submit → save → fresh daemon restores correctly |
| CLI `watch` | Verified: live goal table renders |
| WebSocket reconnect | Implemented: exponential backoff, max 20 retries |
| Step sync | Fixed: `_sync_goal_steps()` keeps `Goal.steps` in sync |
| Note parsing | Fixed: wider trigger set + `_split_note()` in offline fallback |

## Breaking Changes

None.

## Migration

None required.

## Known Issues

- `tests/test_browser.py:7` has a pre-existing I001 import-sort lint exclusion
  (unrelated to this release).
- Live browser automation requires Playwright + Chromium
  (`pip install playwright && playwright install chromium`). Without it,
  `browser.*` capabilities fail gracefully with a clear message.
