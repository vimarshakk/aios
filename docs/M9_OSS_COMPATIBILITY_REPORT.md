# Upstream Compatibility Report

**Date:** 2025-07-17
**Milestone:** M9 — OSS Integration Layer

---

## Compatibility Matrix

Each adapter is designed to work with the latest stable release of its upstream project. Upstream packages are optional dependencies — AIOS does not vendor or fork them.

| Adapter | Upstream | Tested Version | Min Version | Breaking Risk | Notes |
|---------|----------|---------------|-------------|---------------|-------|
| OpenJarvis | openjarvis | latest | 0.1.0+ | Low | Stable API surface |
| OpenHands | openhands | latest | 0.1.0+ | Low | Well-versioned releases |
| OpenInterpreter | open-interpreter | latest | 0.1.0+ | Medium | v0.4.x had breaking CLI changes |
| AnythingLLM | anythingllm | latest | 0.1.0+ | Low | REST API stable |
| LibreChat | librechat | latest | 0.1.0+ | Low | API versioned |
| Open WebUI | open-webui | latest | 0.1.0+ | Medium | Fast-moving, API evolves |
| Continue | continue | latest | 0.1.0+ | Low | Stable MCP protocol |
| Jan | jan | latest | 0.1.0+ | Medium | API versioning in progress |

## Update Strategy

1. **Pin nothing** — adapters import upstream at runtime, not compile time
2. **Version detection** — each adapter reports `upstream_version` from the installed package
3. **Graceful degradation** — if upstream is missing, `is_available` returns `False` and `execute()` returns error result
4. **No vendoring** — upstream code is not copied into AIOS; adapters call upstream APIs

## Breaking Change Handling

When an upstream project introduces breaking changes:

1. The adapter's `execute()` method may fail for affected actions
2. `health_check()` returns unhealthy with descriptive message
3. Fix: update the adapter's action handler to match new upstream API
4. Test: add regression test for the specific action

## Compatibility Testing

- All 96 OSS integration tests run with mocked upstream packages
- Tests verify adapter behavior independent of actual upstream installation
- Real upstream integration tested via `is_available` check at runtime

## Risk Assessment

**Low risk** (5 adapters): OpenJarvis, OpenHands, AnythingLLM, LibreChat, Continue
- Stable APIs, well-versioned releases, established communities

**Medium risk** (3 adapters): OpenInterpreter, Open WebUI, Jan
- Fast-moving projects, API surface may shift
- Mitigated by adapter pattern — only the adapter needs updating, not AIOS core
