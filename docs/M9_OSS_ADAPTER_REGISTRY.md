# Adapter Registry Documentation

**Date:** 2025-07-17
**Milestone:** M9 — OSS Integration Layer

---

## Overview

The Adapter Registry provides a centralized mapping of all OSS adapters, enabling factory-based creation and bulk registration.

## Registry Structure

```python
ADAPTER_REGISTRY: dict[str, tuple[type[Integration], type[Connector]]] = {
    "openjarvis": (OpenJarvisIntegration, OpenJarvisConnector),
    "openhands": (OpenHandsIntegration, OpenHandsConnector),
    "openinterpreter": (OpenInterpreterIntegration, OpenInterpreterConnector),
    "anythingllm": (AnythingLLMIntegration, AnythingLLMConnector),
    "librechat": (LibreChatIntegration, LibreChatConnector),
    "openwebui": (OpenWebUIIntegration, OpenWebUIConnector),
    "continue": (ContinueIntegration, ContinueConnector),
    "jan": (JanIntegration, JanConnector),
}
```

## Factory Functions

### `create_oss_integration(name, config?)`

Creates an integration instance by name.

```python
from aios.integrations.oss import create_oss_integration
from aios.integrations.types import IntegrationConfig

# With default config
integ = create_oss_integration("openjarvis")

# With custom config
config = IntegrationConfig(name="openjarvis", base_url="http://localhost:8080")
integ = create_oss_integration("openjarvis", config)
```

**Raises:** `ValueError` if name is not a known adapter.

### `create_oss_connector(name, integration)`

Creates a connector backed by the given integration.

```python
from aios.integrations.oss import create_oss_integration, create_oss_connector

integ = create_oss_integration("openhands")
connector = create_oss_connector("openhands", integ)
```

**Raises:** `ValueError` if name is not a known adapter.

### `register_all_oss(integration_registry, connector_registry, config_factory?)`

Registers all 8 adapters into both registries.

```python
from aios.integrations.oss import register_all_oss
from aios.integrations.registry import IntegrationRegistry
from aios.integrations.connector import ConnectorRegistry

int_reg = IntegrationRegistry()
conn_reg = ConnectorRegistry()

results = register_all_oss(int_reg, conn_reg)
# results = {
#   "openjarvis": {"available": True, "integration_registered": True, "connector_registered": True},
#   ...
# }
```

## Upstream Metadata

### `UPSTREAM_VERSIONS`

```python
UPSTREAM_VERSIONS: dict[str, str | None] = {
    "openjarvis": "0.1.0",  # or None if not installed
    "openhands": "0.1.0",
    ...
}
```

### `UPSTREAM_LICENSES`

```python
UPSTREAM_LICENSES: dict[str, str] = {
    "openjarvis": "MIT",
    "openhands": "MIT",
    "openinterpreter": "MIT",
    "anythingllm": "MIT",
    "librechat": "MIT",
    "openwebui": "BSD-2-Clause",
    "continue": "Apache-2.0",
    "jan": "AGPL-3.0",
}
```

## Available Adapter Names

```
anythingllm
continue
jan
librechat
openhands
openinterpreter
openjarvis
openwebui
```

## Usage Patterns

### Check availability before connect

```python
integ = create_oss_integration("openhands")
if integ.is_available:
    await integ.connect()
    result = await integ.execute("run_task", task="fix bug #42")
```

### Bulk registration

```python
results = register_all_oss(integration_registry, connector_registry)
for name, status in results.items():
    print(f"{name}: available={status['available']}, registered={status['integration_registered']}")
```

### Discover registered adapters

```python
from aios.integrations.oss import ADAPTER_REGISTRY

for name, (int_cls, conn_cls) in ADAPTER_REGISTRY.items():
    print(f"{name}: {int_cls.__name__} + {conn_cls.__name__}")
```
