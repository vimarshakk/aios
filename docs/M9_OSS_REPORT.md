# OSS Integration Report

**Date:** 2025-07-17
**Milestone:** M9 — OSS Integration Layer

---

## Overview

AIOS wraps 8 upstream open-source projects behind a unified adapter layer. Each adapter provides a consistent lifecycle interface (`connect`, `disconnect`, `health_check`, `execute`) while preserving upstream licenses and enabling independent updates.

## Design Principles

1. **No forking** — business logic stays in upstream repositories
2. **Adapter pattern** — AIOS → Adapter → Upstream Project
3. **Optional dependencies** — upstream packages are not required; adapters report availability at runtime
4. **License preservation** — every adapter documents and carries its upstream license
5. **Independent updates** — upstream projects can be updated without modifying AIOS code

## Adapter Inventory

| Adapter | Upstream Project | License | Purpose |
|---------|-----------------|---------|---------|
| OpenJarvis | openjarvis | MIT | Workflow engine, scheduler, evaluations, reasoning |
| OpenHands | openhands | MIT | Coding agent, sandbox, git, browser-assisted coding |
| OpenInterpreter | open-interpreter | MIT | Desktop agent, shell/python execution, file operations |
| AnythingLLM | anythingllm | MIT | Document ingestion, embeddings, RAG, retrieval |
| LibreChat | librechat | MIT | Conversation management, artifacts, session management |
| Open WebUI | open-webui | BSD-2-Clause | Local model management, provider config, inference |
| Continue | continue | Apache-2.0 | IDE support, codebase indexing, autocomplete, MCP |
| Jan | jan | AGPL-3.0 | Model downloads, lifecycle management, versioning |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   AIOS Core                      │
│                                                  │
│  IntegrationRegistry  ConnectorRegistry          │
│         │                    │                   │
│         ▼                    ▼                   │
│  ┌──────────────┐    ┌──────────────┐            │
│  │  Integration  │    │  Connector   │            │
│  │  (lifecycle)  │    │  (bindings)  │            │
│  └──────┬───────┘    └──────┬───────┘            │
│         │                    │                   │
│         ▼                    ▼                   │
│  ┌──────────────────────────────────────┐        │
│  │         OSS Adapter Layer            │        │
│  │                                      │        │
│  │  OpenJarvis    OpenHands             │        │
│  │  OpenInterpreter  AnythingLLM       │        │
│  │  LibreChat     Open WebUI           │        │
│  │  Continue      Jan                  │        │
│  └──────────────────────────────────────┘        │
│                     │                            │
└─────────────────────┼────────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────┐
    │     Upstream OSS Projects       │
    │                                 │
    │  openjarvis   openhands         │
    │  open-interpreter  anythingllm  │
    │  librechat    open-webui        │
    │  continue     jan               │
    └─────────────────────────────────┘
```

## Lifecycle

Each adapter follows the same lifecycle:

```
DISCOVERED → CONFIGURED → CONNECTING → CONNECTED → DISCONNECTING → DISABLED
```

1. **DISCOVERED** — adapter instantiated, availability checked
2. **CONFIGURED** — `configure(config)` called
3. **CONNECTING** — `connect()` in progress
4. **CONNECTED** — upstream ready, `execute()` available
5. **DISCONNECTING** — `disconnect()` in progress
6. **DISABLED** — adapter shut down

## Capability Mapping

Each adapter exposes actions through `ConnectorBinding`:

| Adapter | Capabilities |
|---------|-------------|
| OpenJarvis | workflow.execute, workflow.schedule, evaluation.run, reasoning.invoke, workflow.list, evaluation.list |
| OpenHands | coding.sandbox, coding.git, coding.edit_repository, coding.browse, coding.run_task, coding.list_sessions |
| OpenInterpreter | desktop.shell, desktop.python, desktop.automate, desktop.file_read, desktop.file_write, desktop.file_list, desktop.chat |
| AnythingLLM | rag.ingest, rag.embed, rag.retrieve, rag.query, rag.list_workspaces, rag.list_documents, rag.delete_document, rag.configure |
| LibreChat | conversation.create, conversation.send, conversation.get, conversation.list, conversation.render_markdown, artifact.create, artifact.get, artifact.list, session.create, session.get, session.end |
| Open WebUI | model.list, model.get, model.download, model.delete, provider.configure, provider.list, inference.run, pipeline.list, pipeline.get |
| Continue | ide.index, ide.autocomplete, ide.chat, ide.edit_code, ide.get_definitions, ide.get_references, ide.run_mcp, ide.list_mcp_tools, ide.get_context |
| Jan | model.list, model.get, model.download, model.delete, model.update, model.start, model.stop, engine.list, engine.configure |

## Test Coverage

- 96 OSS integration tests
- 29 base integration tests
- 125 total tests, all passing

## Files

```
packages/integrations/src/aios/integrations/
  base.py                    # Integration ABC
  types.py                   # IntegrationConfig, IntegrationResult, IntegrationStatus
  connector.py               # Connector ABC, ConnectorBinding
  registry.py                # IntegrationRegistry
  oss/
    __init__.py              # Registry, factories, UPSTREAM_VERSIONS, UPSTREAM_LICENSES
    openjarvis.py            # OpenJarvis adapter
    openhands.py             # OpenHands adapter
    openinterpreter.py       # OpenInterpreter adapter
    anythingllm.py           # AnythingLLM adapter
    librechat.py             # LibreChat adapter
    openwebui.py             # Open WebUI adapter
    continue_dev.py          # Continue adapter
    jan.py                   # Jan adapter
    connectors.py            # 8 connector classes
tests/
  test_integrations.py       # 29 base integration tests
  test_oss_integrations.py   # 96 OSS integration tests
```
