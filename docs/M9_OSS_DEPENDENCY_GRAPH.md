# OSS Integration Dependency Graph

**Date:** 2025-07-17
**Milestone:** M9 — OSS Integration Layer

---

## Internal Dependencies

```
aios.integrations.base
  └── (no deps — ABC only)

aios.integrations.types
  └── (no deps — dataclasses only)

aios.integrations.connector
  └── aios.integrations.base
  └── aios.integrations.types

aios.integrations.registry
  └── aios.integrations.base
  └── aios.integrations.types

aios.integrations.oss.__init__
  └── aios.integrations.oss.openjarvis
  └── aios.integrations.oss.openhands
  └── aios.integrations.oss.openinterpreter
  └── aios.integrations.oss.anythingllm
  └── aios.integrations.oss.librechat
  └── aios.integrations.oss.openwebui
  └── aios.integrations.oss.continue_dev
  └── aios.integrations.oss.jan
  └── aios.integrations.oss.connectors

aios.integrations.oss.openjarvis
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] openjarvis (upstream)

aios.integrations.oss.openhands
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] openhands (upstream)

aios.integrations.oss.openinterpreter
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] open_interpreter (upstream)

aios.integrations.oss.anythingllm
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] anythingllm (upstream)

aios.integrations.oss.librechat
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] librechat (upstream)

aios.integrations.oss.openwebui
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] open_webui (upstream)

aios.integrations.oss.continue_dev
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] continue (upstream)

aios.integrations.oss.jan
  └── aios.integrations.base
  └── aios.integrations.types
  └── [optional] jan (upstream)

aios.integrations.oss.connectors
  └── aios.integrations.connector
  └── aios.integrations.oss.openjarvis
  └── aios.integrations.oss.openhands
  └── aios.integrations.oss.openinterpreter
  └── aios.integrations.oss.anythingllm
  └── aios.integrations.oss.librechat
  └── aios.integrations.oss.openwebui
  └── aios.integrations.oss.continue_dev
  └── aios.integrations.oss.jan
```

## Upstream Dependencies (Optional)

All upstream packages are optional. If not installed, the adapter still loads but `is_available` returns `False`.

| Adapter | Import Path | pip install |
|---------|-------------|-------------|
| OpenJarvis | `openjarvis` | `pip install openjarvis` |
| OpenHands | `openhands` | `pip install openhands` |
| OpenInterpreter | `open_interpreter` | `pip install open-interpreter` |
| AnythingLLM | `anythingllm` | `pip install anythingllm` |
| LibreChat | `librechat` | `pip install librechat` |
| Open WebUI | `open_webui` | `pip install open-webui` |
| Continue | `continue` | `pip install continue` |
| Jan | `jan` | `pip install jan` |

## Dependency Direction

```
                    ┌─────────────┐
                    │  AIOS Core  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Integration │
                    │   (ABC)     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐ ┌─────▼─────┐ ┌───▼────────┐
     │  Adapter   │ │ Connector │ │  Registry  │
     │  (8 impls) │ │ (8 impls) │ │            │
     └─────┬──────┘ └───────────┘ └────────────┘
           │
           │ (optional, at runtime)
           ▼
     ┌─────────────┐
     │  Upstream   │
     │  OSS Projects│
     └─────────────┘
```

No circular dependencies exist in the OSS adapter layer.
