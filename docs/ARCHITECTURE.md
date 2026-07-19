# AIOS Architecture

Contributor-facing guide to the AIOS subsystems. For versioning policy see `docs/FROZEN_INTERFACES.md`; for rationale see `docs/adr/`.

---

## 1. Runtime Lifecycle

```
AiosClient (SDK)
  → Gateway (FastAPI REST/WebSocket)
    → Orchestrator (session/state management)
      → Agents subsystem (engine + base agent + tools)
```

**Startup order:**

1. `PluginRuntime.discover()` scans `~/.aios/plugins/` for manifests, loads enabled plugins, registers their tools into `ToolRegistry`.
2. `CapabilityRegistry.discover()` scans all registry modules (providers, memory backends, etc.) and indexes them.
3. `HybridMemoryManager` is instantiated with configured backends (default: short-term + cache).
4. `ContextBuilder` is instantiated with window, summarizer, and ranker defaults.
5. `Gateway` mounts the FastAPI app, injects the `Orchestrator` instance, binds to `0.0.0.0:8787`.
6. `AiosClient` connects via `httpx.AsyncClient` (or test-injected transport).

**Shutdown order:** client → gateway → orchestrator → plugin runtime (`uninstall_all`) → inference engines (`close()`).

---

## 2. Event Flow

```
EventBus (singleton via get_event_bus())
  ├── publish(Event) → all subscribers notified
  ├── subscribe(EventType, handler) → returns unsubscribe fn
  └── history[EventType] → last 1000 events in-memory
```

**Event types** (non-exhaustive):

| Category | Events |
|----------|--------|
| Inference | `INFERENCE_START`, `INFERENCE_END` |
| Tool | `TOOL_CALL_START`, `TOOL_CALL_END` |
| Agent | `AGENT_START`, `AGENT_END`, `AGENT_ERROR` |
| Memory | `MEMORY_UPDATED`, `CONTEXT_UPDATED`, `CONTEXT_STALE` |
| Provider | `MODEL_CHANGED` |
| Workflow | `WORKFLOW_STEP_START`, `WORKFLOW_STEP_END` |
| Session | `SESSION_UPDATED`, `SESSION_ERROR` |

Handlers are async. Errors in one handler do not block others (logged, swallowed). History is ring-buffered at 1000 events with `collections.deque(maxlen=1000)`.

---

## 3. Context Assembly

```
ContextBuilder.build(ContextSpec)
  │
  ├─ window.filter(messages, system, token_budget, overlap)
  │    → WindowMessage[] (sliding window with overlap)
  │
  ├─ summarizer.summarize(messages, model, prompt)
  │    → str (LLM-summarised tail or None)
  │
  ├─ ranker.rank(query, documents, model, top_k)
  │    → RankedDocument[] (scored, deduplicated)
  │
  └─ inject_context(system_prompt, context)
       → str (augmented system prompt)
```

**Flow:** window → summarise → rank → inject. The `ContextWindow` handles token counting (tiktoken-based, falls back to char/4 estimate). Window preserves system messages first, then fills with recent user/assistant pairs until budget is exhausted.

---

## 4. Memory Flow

```
HybridMemoryManager
  ├── ShortTermMemory (deque, FIFO, capacity 100)
  ├── EpisodicMemory (in-memory list + FTS)
  ├── EntityMemory (frozenset-backed index)
  ├── CacheMemory (TTL 300s, LRU eviction)
  └── LongTermMemory (in-memory list, no persistence yet)
```

**Store path:** `store(content, metadata)` → routes to backends based on `metadata.get("memory_type")`. Default: short-term + cache.

**Retrieve path:** `retrieve(query, top_k)` → fan-out to all registered backends, merge, sort by score descending, return top_k `RetrievalResult` items.

**Ranking:** Results are scored by the backend (0.0–1.0). `ContextRanker.rank()` re-scores by relevance to the query string (overlap heuristic). Default hybrid config weights: short-term 1.0, cache 1.0, episodic 0.8, entity 0.8, long-term 0.6.

---

## 5. Plugin Lifecycle

```
PluginManifest.from_yaml(text)        # parse + validate
    │
PluginRuntime.discover(plugin_dir)    # scan manifest.yaml files
    │
PluginRuntime.install(plugin_dir)     # add to registry
    │
PluginRuntime.enable(plugin_id)       # status → ENABLED, load module
    │
PluginRuntime.disable(plugin_id)      # status → DISABLED, unload
    │
PluginRuntime.uninstall(plugin_id)    # remove from registry
    │
PluginRuntime.uninstall_all()         # cleanup on shutdown
```

**Sandbox** is advisory only (M1): `PluginSandbox` wraps `sandbox_call()` which runs the tool function directly. In production, this would be `subprocess.run()` with uid/gid isolation. `SandboxConfig` supports `uid`, `gid`, `network_access`, `timeout_seconds`.

**Manifest format:**

```yaml
name: my-plugin
version: "1.0.0"
description: "..."
tools:
  - name: my_tool
    description: "..."
    parameters:
      type: object
      properties:
        query: { type: string }
      required: [query]
```

---

## 6. Provider Lifecycle

```
EngineFactory.create(name="ollama", model="llama3.2")
  → OllamaEngine(base_url, timeout, max_retries)
  → async with engine:
      result = await engine.complete(messages, tools, tool_choice)
      chunks = [c async for c in engine.stream(messages)]
```

**Engines:** `OllamaEngine`, `OpenAIEngine`, `AnthropicEngine`. All implement `InferenceEngine` ABC (v1 interface). `EngineFactory.create()` returns a `BaseConnector` (inferred from engine name).

**Retry policy:** `RetryPolicy(max_retries=3, base_delay=1.0, backoff_factor=2.0, jitter=True)`. Exponential backoff with full jitter. Used by `@retry_async` decorator.

**Health:** `engine.health()` returns `ProviderHealth(status, latency_ms, error)`. Status is `ProviderStatus.HEALTHY`, `DEGRADED`, or `DOWN`.

---

## 7. Permission Evaluation

```
PermissionChecker(required_perms, on_request)
  │
  on_request(PermissionSet) → bool
  │
  └─ eval() → PermissionSet (allowed) | raises PermissionDenied
```

**Flow:** `eval()` calls `on_request` with the full `PermissionSet` to be granted. The callback decides: return `True` to allow, `False` to deny. If denied, `PermissionDenied` is raised.

**Permission constants:** `FILESYSTEM_READ`, `FILESYSTEM_WRITE`, `NETWORK_HTTP`, `NETWORK_SOCKET`, `PROCESS_EXEC`, `ENVIRONMENT_READ`, `ENVIRONMENT_WRITE`, `PLUGIN_INSTALL`, `PLUGIN_UNINSTALL`, `MEMORY_READ`, `MEMORY_WRITE`.

**PermissionSet.has(perm)** checks membership. `PermissionSet.add(perm)` / `PermissionSet.remove(perm)` mutate the set. `PermissionSet.granted` returns frozen `frozenset`.

---

## 8. Workflow Execution

```
WorkflowPlanner.plan("build me a web scraper")
  → Workflow(steps=[Step, Step, Step], metadata={...})

WorkflowExecutor.run(workflow, memory)
  │
  └─ for each step:
       1. Check dependencies (all upstream steps completed)
       2. eval_conditions(step, memory) → skip if conditions false
       3. request_approval(step) → skip if declined
       4. _execute_step(step, memory) → run with retry
       5. store result in memory for downstream steps
```

**StepStatus:** `PENDING` → `RUNNING` → `COMPLETED` | `FAILED` | `SKIPPED`.

**Retry:** `_execute_step` uses `@retry_async` with the workflow's `RetryPolicy`. On failure, step status is `FAILED`, no more retries attempted for that step.

**Parallel:** Steps with satisfied dependencies run concurrently via `asyncio.gather()`. Steps that depend on incomplete upstream steps are skipped.

**Approval:** `ApprovalPolicy.ALWAYS` → always ask. `AUTO` → skip approval. `ask_fn(step, memory) → bool` for custom logic.

---

## 9. Gateway Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | System health (all subsystems) |
| `POST` | `/chat` | Chat completion (streaming) |
| `GET` | `/agents` | List agents |
| `POST` | `/agents` | Create agent |
| `GET` | `/agents/{id}/status` | Agent status |
| `POST` | `/tools` | Register tool |
| `GET` | `/tools` | List tools |
| `GET` | `/providers` | List providers |
| `POST` | `/providers/{name}/health` | Check provider health |
| `GET` | `/sessions` | List sessions |
| `POST` | `/sessions` | Create session |
| `DELETE` | `/sessions/{id}` | Delete session |
| `GET` | `/config` | System config |
| `PUT` | `/config` | Update config |

---

## 10. Test Structure

All tests live in `tests/` at the repo root. No tests in `packages/` or `services/` directories (import issue with namespace packages).

| File | Covers | Tests |
|------|--------|-------|
| `test_providers.py` | Provider layer, retry, factory | 20 |
| `test_context.py` | Context engine (window, summarizer, ranker, builder) | 35 |
| `test_memory_backends.py` | 5 memory backends | 34 |
| `test_memory_manager.py` | HybridMemoryManager | 30 |
| `test_workflows.py` | Workflow engine (7 modules) | 55 |
| `test_registry.py` | Capability registry, 12 typed registries | 35 |
| `test_permissions.py` | Permission checker | 30 |
| `test_plugins.py` | Plugin manifest, runtime, sandbox, loader | 26 |
| `test_sdk.py` | AiosClient, CLI | 17 |
| `test_contracts.py` | Frozen interface stability | 70 |

**Total: 352+ tests** (contract tests are the guard rail for interface stability).

**Running:**
```bash
uv run pytest tests/ -q --tb=short          # all tests
uv run --with ruff ruff check .              # lint
uv run pytest tests/test_contracts.py -v     # verify interfaces
```
