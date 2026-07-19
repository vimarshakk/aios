# M9 — OSS Integration Layer

**Objective:** Wrap 8 upstream open-source projects behind AIOS adapters without forking business logic.

**Status:** Complete

---

## Sub-milestones

| ID | Name | Priority | Status |
|----|------|----------|--------|
| M9.1 | OpenJarvis Adapter | High | Complete |
| M9.2 | OpenHands Adapter | High | Complete |
| M9.3 | OpenInterpreter Adapter | High | Complete |
| M9.4 | AnythingLLM Adapter | High | Complete |
| M9.5 | LibreChat Adapter | Medium | Complete |
| M9.6 | Open WebUI Adapter | Medium | Complete |
| M9.7 | Continue Adapter | Medium | Complete |
| M9.8 | Jan Adapter | Medium | Complete |
| M9.9 | Adapter Registry + Connectors | High | Complete |
| M9.10 | Integration Validation | High | Complete |
| M9.11 | OSS Integration Documentation | Medium | Complete |

---

## Architecture

```
AIOS Interface → Adapter → Upstream Project
```

Each adapter:
- Subclasses `Integration` (lifecycle: connect/disconnect/execute)
- Wraps an upstream OSS project behind AIOS capabilities
- Reports availability at runtime (upstream packages are optional)
- Preserves upstream license and attribution
- Remains independently updatable

## Upstream Projects

| Adapter | Upstream | License | Capabilities |
|---------|----------|---------|-------------|
| OpenJarvis | openjarvis | MIT | workflow, scheduling, evaluation, reasoning |
| OpenHands | openhands | MIT | coding sandbox, git, browser-assisted coding |
| OpenInterpreter | open-interpreter | MIT | desktop agent, shell/python, file ops |
| AnythingLLM | anythingllm | MIT | document ingestion, embeddings, RAG |
| LibreChat | librechat | MIT | conversations, artifacts, sessions |
| Open WebUI | open-webui | BSD-2-Clause | model management, providers, inference |
| Continue | continue | Apache-2.0 | IDE support, codebase indexing, MCP |
| Jan | jan | AGPL-3.0 | model downloads, lifecycle, versioning |

## Files

```
packages/integrations/src/aios/integrations/
  oss/
    __init__.py              # Registry, factories, UPSTREAM_VERSIONS, UPSTREAM_LICENSES
    openjarvis.py            # OpenJarvis adapter
    openhands.py             # OpenHands adapter
    openinterpreter.py       # OpenInterpreter adapter
    anythingllm.py           # AnythingLLM adapter
    librechat.py             # LibreChat adapter
    openwebui.py             # Open WebUI adapter
    continue_dev.py          # Continue adapter (renamed from continue.py)
    jan.py                   # Jan adapter
    connectors.py            # 8 connector classes
tests/
  test_oss_integrations.py   # 96 integration tests
```

## Test Results

- 96/96 OSS integration tests pass
- 29/29 base integration tests pass
- 125/125 total pass
