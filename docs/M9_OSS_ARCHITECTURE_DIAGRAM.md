# OSS Integration Architecture Diagram

**Date:** 2025-07-17
**Milestone:** M9 — OSS Integration Layer

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         AIOS Core                                │
│                                                                  │
│  ┌─────────────────┐          ┌─────────────────┐               │
│  │ IntegrationRegistry │      │ ConnectorRegistry │               │
│  │  - register()      │      │  - register()      │               │
│  │  - get()           │      │  - get()           │               │
│  │  - connect_all()   │      │  - by_capability() │               │
│  │  - disconnect_all()│      │                     │               │
│  └────────┬──────────┘          └────────┬──────────┘               │
│           │                              │                         │
│           ▼                              ▼                         │
│  ┌────────────────────────────────────────────────┐               │
│  │              Adapter Layer                      │               │
│  │                                                 │               │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐          │               │
│  │  │OpenJarvis│ │OpenHands│ │  Open   │          │               │
│  │  │Adapter   │ │Adapter  │ │Interp.  │          │               │
│  │  └────┬────┘ └────┬────┘ └────┬────┘          │               │
│  │       │           │           │                 │               │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐          │               │
│  │  │Anything │ │LibreChat│ │  Open   │          │               │
│  │  │  LLM    │ │ Adapter │ │ WebUI   │          │               │
│  │  └────┬────┘ └────┬────┘ └────┬────┘          │               │
│  │       │           │           │                 │               │
│  │  ┌─────────┐ ┌─────────┐                      │               │
│  │  │Continue │ │  Jan    │                      │               │
│  │  │ Adapter │ │ Adapter │                      │               │
│  │  └────┬────┘ └────┬────┘                      │               │
│  └───────┼───────────┼───────────────────────────┘               │
│          │           │                                           │
└──────────┼───────────┼───────────────────────────────────────────┘
           │           │
           ▼           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Upstream OSS Projects                          │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │openjarvis│ │openhands │ │  open-   │ │anythingllm│            │
│  │  (MIT)   │ │  (MIT)   │ │interp.   │ │  (MIT)   │            │
│  └──────────┘ └──────────┘ │  (MIT)   │ └──────────┘            │
│                             └──────────┘                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ librechat│ │  open-   │ │ continue │ │   jan    │            │
│  │  (MIT)   │ │  webui   │ │(Apache)  │ │ (AGPL)   │            │
│  └──────────┘ │  (BSD)   │ └──────────┘ └──────────┘            │
│               └──────────┘                                       │
└──────────────────────────────────────────────────────────────────┘
```

## Request Flow

```
User Request
    │
    ▼
AIOS Orchestrator
    │
    ├──► ConnectorRegistry.get("coding.sandbox")
    │         │
    │         ▼
    │    OpenHandsConnector
    │         │
    │         ▼
    │    OpenHandsIntegration.execute("run_sandbox", ...)
    │         │
    │         ▼
    │    openhands.upstream.run_sandbox(...)
    │
    └──► Response
```

## Lifecycle State Machine

```
    ┌────────────┐
    │ DISCOVERED │
    └─────┬──────┘
          │ configure()
          ▼
    ┌────────────┐
    │ CONFIGURED │
    └─────┬──────┘
          │ connect()
          ▼
    ┌────────────┐
    │ CONNECTING │
    └─────┬──────┘
          │ (success)
          ▼
    ┌────────────┐
    │ CONNECTED  │ ◄────── execute() ──────┐
    └─────┬──────┘                          │
          │ disconnect()                    │
          ▼                                 │
    ┌───────────────┐                       │
    │ DISCONNECTING │ ──── (retry) ─────────┘
    └─────┬─────────┘
          │
          ▼
    ┌──────────┐
    │ DISABLED │
    └──────────┘
```

## Connector Binding Pattern

```
Connector
  └── bindings() → [ConnectorBinding, ...]
        │
        ├── ConnectorBinding(
        │     capability="coding.sandbox",
        │     action="run_sandbox",
        │     description="Execute code in a sandbox"
        │   )
        │
        └── ConnectorBinding(
              capability="coding.git",
              action="git_operation",
              description="Perform git operations"
            )
```

The orchestrator resolves `capability` → `ConnectorBinding` → `Integration.execute(action)`.
