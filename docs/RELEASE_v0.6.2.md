# AIOS v0.6.2 — Native Browser Skill (M5 final capability)

**Release date:** 2025-07-18
**Type:** Minor (completes M5 native execution stack)
**Supersedes:** v0.6.1 (daemon + briefings, ADR-0023)

## Summary

M5 is now feature-complete. The final missing native desktop capability —
**browser automation** — is delivered as a first-class `BrowserSkill` built on
the in-repo `aios.browser.BrowserSession` (Playwright/Chromium). AIOS can now
navigate, search, manage tabs, click/type/scroll/screenshot/extract, and
download — fully offline, with a domain allowlist, an SSRF guard against
localhost/internal addresses, confirmation for destructive actions, a
configurable timeout, and an audit log for every action.

The native execution stack is complete: terminal, filesystem, git, docker,
notes, notify, and browser — all resolving natively through the
`CapabilityResolver`; external integrations (Composio/MCP) remain optional
providers preferred only when connected.

## What's New

- `packages/skills/src/aios/skills/native/browser_skill.py`: `BrowserSkill`,
  `BrowserConfigOpts`, `BROWSER_CAPABILITIES`.
- Actions: `open`/`search`/`back`/`forward`/`refresh`, `list_tabs`/`switch_tab`/
  `active_tab`/`close_tab`, `click`/`type`/`press`/`scroll`/`wait_for`/
  `evaluate`/`screenshot`/`extract_text`, `download`/`list_downloads`.
- Security: domain allowlist, localhost/internal deny-by-default (SSRF guard),
  destructive-action confirmation, configurable timeout, audit log.
- Auto-registered with `CapabilityResolver` during `bootstrap()`; exported from
  `aios.skills.native`.
- `aios-browser` added as a workspace dependency of `aios-skills`.

## Quality

- Lint: `ruff check packages/ services/` — clean (new code).
- Tests: **1160 passed, 55 skipped** (full suite, no regressions).
- New tests: `tests/test_browser_skill.py` (11, fake-session injected — no
  browser launch required).
- Frozen interfaces (`Permission`, `PermissionChecker`, `PermissionSet`)
  untouched.

## Upgrade Notes

- Live browser automation requires Playwright + Chromium
  (`pip install playwright && playwright install chromium`). Without it, the
  capability still resolves natively and operations fail gracefully with a
  clear message.
- `BrowserSkill` uses `approval="ask"` for destructive actions; the Supervisor
  approval gate applies when no automated approver is configured.
