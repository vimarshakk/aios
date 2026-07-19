# AIOS v0.3.0 Release Notes

**Release Date:** 2025-07-17
**Type:** Minor feature release (capabilities & ecosystem)

## What's New

### Capability Packages
- **aios-browser** (M3.5): HTTP fetching, HTML parsing, browser automation
- **aios-desktop** (M3.6): Clipboard, notifications, file dialogs, system info
- **aios-vision** (M3.7): Image processing, OCR, screenshot analysis
- **aios-integrations** (M3.8): Third-party service integration framework

### Observability (M3.3) — in aios-telemetry
- `Tracer` with span context propagation
- `MetricsCollector` with counters/gauges/histograms
- `StructuredLogger` with key-value context
- `HealthChecker` with parallel health checks

### Distributed Execution (M3.4) — in aios-distributed
- `TaskMessage`, `PriorityQueue`, `InMemoryQueue`
- `Worker`, `WorkerPool`
- `RetryPolicy`, `DeadLetterQueue`, `TaskPersistence`

### Plugin System (M2) — in aios-plugins
- Plugin SDK: context, capabilities, permissions
- Lifecycle management: start/stop/restart, health checks

### Multi-Agent (M2) — in aios-agents
- `Aggregator` for combining multi-agent results

## Test Statistics
- **Total tests:** 1006 (up from 453 at M1 freeze)
- **Lint:** 0 errors (ruff, strict config)
- **Packages:** 18 (all version 0.3.0)

## Breaking Changes
- None. All frozen interfaces in `docs/FROZEN_INTERFACES.md` unchanged.

## Migration Guide
- No migration needed from v0.1.0/v0.2.0 — backward compatible.

## Known Issues
- Playwright, PIL, and pytesseract are optional dependencies (lazy-imported)
- Integrations platform is a framework; specific service integrations (GitHub, Slack, etc.) are not yet bundled

## Architecture Decision Records
- ADR-0011 through ADR-0018 written (see `docs/adr/`)
