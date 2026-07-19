# AIOS v0.1 — Frozen Public Interfaces

**Frozen:** 2026-07-17  
**Version:** 1.0  
**Status:** Locked until M2

## What Is Frozen

The following interfaces are **locked**. Changes require:
1. A new ADR
2. Version bump (v1 → v2)
3. Deprecation period (minimum 2 minor versions)
4. Migration guide

## Frozen Interfaces

### Runtime

| Interface | Module | Key Methods |
|---|---|---|
| `EventBus` | `aios.agents.events` | `subscribe`, `unsubscribe`, `publish`, `history` |
| `Event` | `aios.agents.events` | `event_type`, `timestamp`, `data` |
| `EventType` | `aios.agents.events` | All enum values |

### Agents

| Interface | Module | Key Methods |
|---|---|---|
| `BaseAgent` (ABC) | `aios.agents.base` | `run`, `step`, `describe` |
| `InferenceEngine` (ABC) | `aios.agents.engine` | `complete`, `stream`, `health`, `models`, `close`, `describe` |
| `CompletionResult` | `aios.agents.engine` | `content`, `usage`, `model`, `finish_reason`, `tool_calls`, `latency_ms` |
| `Usage` | `aios.agents.engine` | `prompt_tokens`, `completion_tokens`, `total_tokens` |
| `StreamChunk` | `aios.agents.engine` | `content`, `tool_calls`, `finish_reason`, `usage`, `done` |

### Types

| Interface | Module | Key Fields |
|---|---|---|
| `Message` | `aios.agents.types` | `role`, `content`, `tool_calls`, `metadata` |
| `Role` | `aios.agents.types` | `SYSTEM`, `USER`, `ASSISTANT`, `TOOL` |
| `ToolCall` | `aios.agents.types` | `id`, `name`, `arguments` |
| `ToolResult` | `aios.agents.types` | `tool_name`, `content`, `success`, `usage`, `cost_usd` |
| `Conversation` | `aios.agents.types` | `messages`, `add`, `window` |
| `Trace` | `aios.agents.types` | `trace_id`, `query`, `steps`, `result`, `add_step` |

### Registry

| Interface | Module | Key Methods |
|---|---|---|
| `RegistryBase[T]` | `aios.agents.registry` | `register`, `get`, `items`, `keys`, `contains`, `clear` |
| `Capability` | `aios.agents.registry` | `name`, `capability_type`, `version`, `description`, `permissions`, `tags` |
| `CapabilityRegistry` | `aios.agents.registry` | `register`, `discover`, `find`, `get`, `get_entry`, `clear` |

### Permissions

| Interface | Module | Key Methods |
|---|---|---|
| `Permission` | `aios.agents.permissions` | All string constants |
| `PermissionSet` | `aios.agents.permissions` | `has`, `has_all`, `missing`, `granted` |
| `PermissionRequest` | `aios.agents.permissions` | `permissions`, `reason`, `source` |
| `PermissionResult` | `aios.agents.permissions` | `granted`, `denied`, `approved` |
| `PermissionChecker` | `aios.agents.permissions` | `check`, `check_tool`, `enforce`, `enforce_tool`, `grant`, `revoke` |

### Memory

| Interface | Module | Key Methods |
|---|---|---|
| `MemoryBackend` (ABC) | `aios.memory.backend` | `store`, `retrieve`, `delete`, `clear`, `count`, `has`, `close` |
| `RetrievalResult` | `aios.memory.backend` | `content`, `score`, `metadata`, `source`, `doc_id`, `created_at` |
| `HybridMemoryManager` | `aios.memory.manager` | `register`, `unregister`, `enable`, `disable`, `store`, `retrieve`, `delete`, `clear`, `count`, `list_backends`, `get_backend`, `close` |
| `BackendConfig` | `aios.memory.manager` | `name`, `backend`, `weight`, `enabled`, `priority` |
| `MemoryEvent` | `aios.memory.events` | `event_type`, `backend`, `doc_id`, `timestamp`, `metadata` |
| `MemoryEventType` | `aios.memory.events` | All enum values |

### Context

| Interface | Module | Key Methods |
|---|---|---|
| `ContextBuilder` | `aios.context.builder` | `build`, `build_simple` |
| `ContextSpec` | `aios.context.builder` | `query`, `system_prompt`, `conversation`, `max_context_tokens` |
| `BuildResult` | `aios.context.builder` | `messages`, `memory_used`, `was_summarized` |

### Workflows

| Interface | Module | Key Methods |
|---|---|---|
| `Workflow` | `aios.workflows.base` | `id`, `name`, `steps`, `metadata`, `get_step` |
| `WorkflowStep` | `aios.workflows.base` | `id`, `type`, `config`, `dependencies` |
| `WorkflowResult` | `aios.workflows.base` | `workflow_id`, `status`, `step_results`, `error`, `duration` |
| `StepStatus` | `aios.workflows.base` | All enum values |
| `WorkflowExecutor` | `aios.workflows.executor` | `run`, `resume`, `register_handler` |
| `WorkflowPlanner` | `aios.workflows.planner` | `plan`, `plan_deterministic` |

### Plugins

| Interface | Module | Key Methods |
|---|---|---|
| `PluginManifest` | `aios.plugins.manifest` | `name`, `version`, `tools`, `permissions`, `from_yaml`, `from_file` |
| `ToolSpec` | `aios.plugins.manifest` | `name`, `description`, `parameters` |
| `PluginRuntime` | `aios.plugins.runtime` | `install`, `enable`, `disable`, `uninstall`, `get`, `get_tools`, `list_installed`, `mark_error` |
| `PluginStatus` | `aios.plugins.runtime` | All enum values |

### Tools

| Interface | Module | Key Methods |
|---|---|---|
| `BaseTool` (ABC) | `aios.agents.tools` | `execute`, `describe` |
| `ToolSpec` | `aios.agents.tools` | `name`, `description`, `parameters`, `required`, `category` |
| `BaseConnector` (ABC) | `aios.agents.tools` | `connect`, `disconnect`, `query` |

### Gateway + SDK

| Interface | Module | Key Methods |
|---|---|---|
| `AiosClient` | `aios.sdk.client` | `chat`, `health`, `list_agents`, `list_tools`, `set_session`, `clear_session`, `close` |
| `ChatResult` | `aios.sdk.client` | `response`, `agent`, `session_id`, `messages` |
| `ChatMessage` | `aios.sdk.client` | `role`, `content` |
| Gateway REST | `aios.gateway.main` | `POST /chat`, `GET /health`, `GET /agents`, `GET /tools` |
| Gateway WebSocket | `aios.gateway.main` | `WS /ws/chat` |
| CLI | `aios.sdk.cli` | `chat`, `agent`, `tool`, `provider`, `status`, `config` |

### Orchestrator

| Interface | Module | Key Methods |
|---|---|---|
| `Orchestrator` | `aios.orchestrator.main` | `register_agent`, `register_tool`, `route`, `call_tool`, `get_or_create_session` |
| `Session` | `aios.orchestrator.main` | `id`, `conversation`, `metadata`, `agent_name` |

## What Is NOT Frozen

- Internal implementations of all the above (can be optimized, refactored)
- New `EventType` values (can be added)
- New `Permission` constants (can be added)
- New `RegistryBase` subclasses (can be added)
- New `MemoryBackend` implementations (can be added)
- New `InferenceEngine` implementations (can be added)
- CLI commands (can be added)
- Gateway endpoints (can be added)
- Test infrastructure
- Build configuration

## Versioning Strategy

- Interfaces are versioned at the **module level** via `API_VERSION = "1.0"` in `__init__.py`.
- Breaking changes to frozen interfaces require `API_VERSION` bump (1.0 → 2.0).
- Non-breaking additions (new methods with defaults, new enum values) are allowed within v1.
- Deprecation: Old signatures emit `DeprecationWarning` for 2 minor versions before removal.
