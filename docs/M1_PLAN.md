# AIOS M1 Development Plan

## Current State Assessment

### What exists (working)
| Component | Status | Tests |
|---|---|---|
| Core types (Message, ToolCall, ToolResult, etc.) | ✅ | 20 tests |
| EventBus (17 events, thread-safe) | ✅ | 9 tests |
| RegistryBase (8 typed registries) | ✅ | 11 tests |
| InferenceEngine ABC | ⚠️ type mismatch | — |
| ReAct Agent | ✅ | 12 tests |
| BaseTool / BaseConnector ABCs | ✅ | — |
| MCPBridge | ✅ | 4 tests |
| CalculatorTool, DateTimeTool, WebFetchTool | ✅ | 10 tests |
| FactStore + JSONLFactStore | ✅ | 7 tests |
| VoicePipeline (VAD/STT/TTS) | ✅ | 3 tests |
| TaskScheduler | ✅ | 8 tests |
| Gateway (FastAPI REST+WS) | ⚠️ stub | — |
| Orchestrator | ⚠️ no smart routing | 8 tests |
| 8 vendor repos cloned | ✅ reference only | — |

### Critical gaps identified
1. **InferenceEngine ABC** returns `str` — should return rich dict with usage/timing/tool_calls
2. **ReActAgent** passes `model: str` but ABC expects `model: ModelSpec`
3. **No provider implementations** — no Ollama, no OpenAI adapter
4. **No context engine** — agents build prompts manually
5. **No workflow engine** — orchestration is just agent dispatch
6. **No permissions model** — tools have no permission declarations
7. **No plugin runtime** — no manifest, no lifecycle
8. **Memory is primitive** — only JSONL facts and Qdrant vectors, no unified API
9. **Gateway is a stub** — `/chat` returns placeholder string
10. **vendor/ not gitignored** — will bloat the repo
11. **No CLI/SDK** — no way to interact with AIOS from terminal

---

## Architecture Principles (from feedback)

1. **Integrate, don't extract** — Thin adapters around capabilities, not forks
2. **Provider-independent** — Swap Ollama for OpenAI with config, not code
3. **Event-driven** — All communication through EventBus
4. **Capability discovery** — Registry for everything, no static imports
5. **Permission-first** — Every tool declares what it needs
6. **Context is king** — Every invocation builds rich context automatically
7. **Workflow ≠ Agent** — Planning lives outside the agent loop

---

## Phase 1: Provider Layer (Week 1)

**Goal:** Replace the stub InferenceEngine ABC with a production-quality interface, then implement adapters for Ollama, OpenAI, and Anthropic.

### 1.1 Fix InferenceEngine ABC

**File:** `packages/agents/src/aios/agents/engine.py`

The ABC currently returns `str` from `complete()`. The OpenJarvis pattern is strictly better — return a rich dict:

```python
@dataclass
class CompletionResult:
    content: str
    usage: Usage
    model: str
    finish_reason: str
    tool_calls: list[ToolCall]
    latency_ms: float
    raw: dict  # provider-specific response

class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class InferenceEngine(ABC):
    async def complete(self, messages, *, model, temperature, max_tokens, **kwargs) -> CompletionResult
    async def stream(self, messages, *, model, temperature, max_tokens, **kwargs) -> AsyncIterator[StreamChunk]
    async def health(self) -> bool
    async def models(self) -> list[str]
    def close(self) -> None
```

**Changes:**
- Add `CompletionResult`, `Usage`, `StreamChunk` dataclasses
- Change `complete()` return type from `str` to `CompletionResult`
- Add `close()` method
- Add `models()` returning `list[str]` (not `list[ModelSpec]` — keep it simple)

### 1.2 Create provider package

```
packages/providers/
  pyproject.toml
  src/aios/providers/
    __init__.py
    base.py          # Re-export from agents.engine
    ollama.py        # Ollama adapter (native API)
    openai.py        # OpenAI adapter (openai SDK)
    anthropic.py     # Anthropic adapter (anthropic SDK)
    litellm.py       # LiteLLM adapter (unified 100+ providers)
    openai_compat.py # Shared base for vLLM, SGLang, llama.cpp, LM Studio
    factory.py       # create_engine(name, config) -> InferenceEngine
```

### 1.3 Ollama adapter

**Key design decisions:**
- Use native Ollama API (`/api/chat`) for best performance
- Use `httpx.AsyncClient` with connection pooling
- Support both streaming and non-streaming
- Convert Ollama's nanosecond durations to milliseconds
- Handle tool_calls (dict args → JSON string conversion)
- Support `OLLAMA_HOST` env var (default `http://localhost:11434`)

### 1.4 OpenAI adapter

- Use `openai` SDK (already in dependencies)
- Support `OPENAI_API_KEY` and `OPENAI_BASE_URL` for OpenAI-compatible endpoints
- Handle streaming via SSE
- Convert tool_calls to AIOS format

### 1.5 Anthropic adapter

- Use `anthropic` SDK (already in dependencies)
- Support `ANTHROPIC_API_KEY`
- Handle Claude's message format (system as separate param)

### 1.6 Factory

```python
def create_engine(name: str, **config) -> InferenceEngine:
    """Create an engine by name."""
    engines = {
        "ollama": OllamaEngine,
        "openai": OpenAIEngine,
        "anthropic": AnthropicEngine,
        "litellm": LiteLLMEngine,
    }
    return engines[name](**config)
```

### 1.7 Fix ReActAgent

Update to use `CompletionResult`:
- Extract `result.content` instead of raw string
- Track usage from `result.usage`
- Handle `result.tool_calls` for native function calling

### 1.8 Tests

Each provider gets unit tests with mocked HTTP responses. No real API calls in CI.

---

## Phase 2: Context Engine (Week 2)

**Goal:** Every agent invocation automatically builds rich context from conversation, memory, and system prompt.

### 2.1 Create context package

```
packages/context/
  pyproject.toml
  src/aios/context/
    __init__.py
    builder.py       # ContextBuilder — assembles context for every invocation
    retriever.py     # MemoryRetriever — semantic search from vector store
    summarizer.py    # ContextSummarizer — compress long conversations
    window.py        # ConversationWindow — sliding window management
    ranking.py       # RelevanceRanker — score and filter retrieved context
    inject.py        # inject_context() — prepend context to messages
```

### 2.2 ContextBuilder

```python
class ContextBuilder:
    """Build complete context for an agent invocation."""
    
    async def build(
        self,
        query: str,
        conversation: Conversation,
        *,
        memory: MemoryBackend | None = None,
        system_prompt: str = "",
        max_context_tokens: int = 8000,
    ) -> list[Message]:
        """
        1. Start with system prompt
        2. Retrieve relevant memory (semantic search)
        3. Summarize old conversation if too long
        4. Add recent conversation (sliding window)
        5. Add user query
        6. Return assembled messages
        """
```

### 2.3 Retriever

```python
class MemoryRetriever:
    """Retrieve relevant context from memory backends."""
    
    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> list[RetrievalResult]:
        """Semantic search across all memory backends."""
```

### 2.4 Window + Summarizer

```python
class ConversationWindow:
    """Manage conversation sliding window with token counting."""
    
    def fit(self, messages: list[Message], max_tokens: int) -> list[Message]:
        """Return messages that fit within token budget."""

class ContextSummarizer:
    """Summarize old conversation turns to save context space."""
    
    async def summarize(self, messages: list[Message]) -> str:
        """Use LLM to summarize old messages."""
```

### 2.5 Integration

Update ReActAgent to use ContextBuilder instead of manually building prompts:
```python
# Before (manual)
messages = [
    Message(role=Role.SYSTEM, content=system_prompt),
    Message(role=Role.USER, content=query),
]

# After (automatic)
builder = ContextBuilder()
messages = await builder.build(query, conversation, memory=memory)
```

---

## Phase 3: Unified Memory (Week 2-3)

**Goal:** Single Memory API that abstracts over different storage backends.

### 3.1 Create memory package (extend existing)

```
packages/memory/src/aios/memory/
  __init__.py          # Updated exports
  backend.py           # MemoryBackend ABC (unified interface)
  short_term.py        # Conversation sliding window
  long_term.py         # Vector-backed semantic memory
  episodic.py          # Timestamped interaction memory
  entity.py            # Entity-relationship memory
  cache.py             # LRU cache for frequent queries
  fact_store.py        # Existing (unchanged)
  vector_store.py      # Existing (unchanged)
```

### 3.2 Unified MemoryBackend ABC

```python
class MemoryBackend(ABC):
    @abstractmethod
    async def store(self, content: str, *, metadata: dict = None) -> str: ...
    
    @abstractmethod
    async def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]: ...
    
    @abstractmethod
    async def delete(self, doc_id: str) -> bool: ...
    
    @abstractmethod
    async def clear(self) -> None: ...

@dataclass
class RetrievalResult:
    content: str
    score: float
    metadata: dict
    source: str
```

### 3.3 Implementations

- **ShortTermMemory**: In-memory list with token budget (already partially exists as Conversation)
- **LongTermMemory**: Qdrant + sentence-transformers (already exists as VectorMemory, just needs API alignment)
- **EpisodicMemory**: Timestamped entries, useful for "what did we discuss last time"
- **EntityMemory**: Extract and store entities (person, place, thing), useful for personalization
- **CacheMemory**: LRU cache for frequently accessed facts

---

## Phase 4: Workflow Engine (Week 3)

**Goal:** Separate planning from execution. Workflows live outside the agent.

### 4.1 Create workflow package

```
packages/workflows/
  pyproject.toml
  src/aios/workflows/
    __init__.py
    base.py          # WorkflowStep, Workflow, WorkflowResult
    planner.py       # LLM-based task decomposition
    executor.py      # Step-by-step execution
    state.py         # WorkflowState (persisted in Redis/SQLite)
    retry.py         # RetryPolicy (exponential backoff, max retries)
    parallel.py      # Parallel step execution
    approval.py      # Human-in-the-loop approval steps
    conditions.py    # Conditional branching
```

### 4.2 Core types

```python
class WorkflowStep:
    id: str
    type: str  # "agent_call", "tool_call", "condition", "approval", "parallel"
    config: dict
    dependencies: list[str]  # step IDs this depends on

class Workflow:
    id: str
    name: str
    steps: list[WorkflowStep]
    state: WorkflowState

class WorkflowState:
    status: str  # "pending", "running", "paused", "completed", "failed"
    current_step: str | None
    results: dict[str, Any]
    created_at: float
    updated_at: float
```

### 4.3 Planner

```python
class WorkflowPlanner:
    """Use LLM to decompose a task into workflow steps."""
    
    async def plan(self, task: str, available_tools: list[ToolSpec]) -> Workflow:
        """Break task into steps with dependencies."""
```

### 4.4 Executor

```python
class WorkflowExecutor:
    """Execute workflow steps, respecting dependencies and state."""
    
    async def run(self, workflow: Workflow) -> WorkflowResult:
        """Execute all ready steps in topological order."""
```

---

## Phase 5: Capability Registry (Week 3-4)

**Goal:** Dynamic discovery of everything — agents, tools, skills, providers, plugins, prompts, workflows.

### 5.1 Expand registry system

**File:** `packages/agents/src/aios/agents/registry.py`

Add new typed registries:
```python
class SkillRegistry(RegistryBase[Any]): ...      # Already exists
class PluginRegistry(RegistryBase[Any]): ...     # New
class PromptRegistry(RegistryBase[Any]): ...     # New
class WorkflowRegistry(RegistryBase[Any]): ...   # New
class ProviderRegistry(RegistryBase[Any]): ...   # New
```

### 5.2 Capability metadata

```python
@dataclass
class Capability:
    name: str
    type: str  # "agent", "tool", "skill", "provider", "plugin", "prompt", "workflow"
    version: str
    description: str
    permissions: list[str]
    tags: list[str]
    entry_point: Any  # callable or class
```

### 5.3 Discovery

```python
class CapabilityRegistry:
    """Unified registry for all AIOS capabilities."""
    
    def discover(self) -> list[Capability]:
        """List all registered capabilities."""
    
    def find(self, query: str, *, type: str = None) -> list[Capability]:
        """Search capabilities by name/description/tags."""
    
    def get(self, name: str, type: str) -> Capability:
        """Get specific capability by name and type."""
```

---

## Phase 6: Permissions Model (Week 4)

**Goal:** Every tool declares what it needs. Runtime enforces.

### 6.1 Permission types

```python
class Permission:
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    NETWORK_HTTP = "network.http"
    NETWORK_TCP = "network.tcp"
    DESKTOP_MOUSE = "desktop.mouse"
    DESKTOP_KEYBOARD = "desktop.keyboard"
    PROCESS_EXEC = "process.exec"
    DATABASE_READ = "database.read"
    DATABASE_WRITE = "database.write"
    VOICE_RECORD = "voice.record"
    SCREEN_CAPTURE = "screen.capture"
```

### 6.2 Tool permission declaration

```python
class BaseTool(ABC):
    permissions: list[str] = []  # Override in subclasses
    
    # Example:
    # class ShellTool(BaseTool):
    #     permissions = ["process.exec", "filesystem.read"]
```

### 6.3 PermissionChecker

```python
class PermissionChecker:
    """Enforce permissions before tool execution."""
    
    def check(self, tool: BaseTool, granted: list[str]) -> bool:
        """Return True if all tool permissions are granted."""
    
    def request(self, permissions: list[str]) -> bool:
        """Request permissions from user (UI integration point)."""
```

---

## Phase 7: Plugin Runtime (Week 4-5)

**Goal:** Dynamic plugin installation with manifests.

### 7.1 Plugin manifest

```yaml
# plugin.yaml
name: github
version: 1.0.0
description: GitHub integration
author: aios
permissions:
  - network.http
tools:
  - name: create_issue
    description: Create a GitHub issue
    parameters:
      repo: { type: string, required: true }
      title: { type: string, required: true }
      body: { type: string }
  - name: create_pr
    description: Create a pull request
events:
  - GitHubWebhook
skills:
  - code_review
```

### 7.2 Plugin runtime

```
packages/plugins/
  pyproject.toml
  src/aios/plugins/
    __init__.py
    manifest.py     # PluginManifest dataclass
    loader.py       # Load plugin from directory/zip
    runtime.py      # PluginRuntime (install, enable, disable, update)
    sandbox.py      # Plugin isolation (optional)
```

### 7.3 Plugin API

```python
class PluginRuntime:
    """Manage plugin lifecycle."""
    
    def install(self, path: str) -> Plugin: ...
    def enable(self, name: str) -> None: ...
    def disable(self, name: str) -> None: ...
    def uninstall(self, name: str) -> None: ...
    def list_installed(self) -> list[Plugin]: ...
    def get_tools(self, plugin: str) -> list[BaseTool]: ...
```

---

## Phase 8: Gateway + CLI (Week 5)

**Goal:** Working gateway and command-line interface.

### 8.1 Fix Gateway

**File:** `services/gateway/src/aios/gateway/main.py`

Wire the `/chat` endpoint to the orchestrator:
```python
@app.post("/chat")
async def chat(request: ChatRequest):
    response = await orchestrator.route(
        query=request.message,
        session_id=request.session_id,
    )
    return ChatResponse(response=response, session_id=...)
```

### 8.2 CLI

```
packages/sdk/
  pyproject.toml
  src/aios/sdk/
    __init__.py
    cli.py         # Click/typer CLI
    client.py      # Python SDK client
```

Commands:
```bash
aios chat "What's the weather?"
aios agent list
aios tool list
aios provider list
aios plugin install ./my-plugin
aios memory search "what did we discuss"
aios workflow run research-task "Find info about X"
aios config set provider ollama
aios status
```

---

## Implementation Order

```
Phase 1: Provider Layer ────────────────────── Week 1
  1.1 Fix InferenceEngine ABC + CompletionResult
  1.2 Create packages/providers/
  1.3 Ollama adapter
  1.4 OpenAI adapter
  1.5 Anthropic adapter
  1.6 Factory
  1.7 Fix ReActAgent
  1.8 Provider tests

Phase 2: Context Engine ────────────────────── Week 2
  2.1 Create packages/context/
  2.2 ContextBuilder
  2.3 MemoryRetriever
  2.4 Window + Summarizer
  2.5 Integration with ReActAgent

Phase 3: Unified Memory ───────────────────── Week 2-3
  3.1 Extend packages/memory/
  3.2 MemoryBackend ABC
  3.3 Implementations (ShortTerm, LongTerm, Episodic, Entity, Cache)

Phase 4: Workflow Engine ──────────────────── Week 3
  4.1 Create packages/workflows/
  4.2 Core types
  4.3 Planner
  4.4 Executor

Phase 5: Capability Registry ─────────────── Week 3-4
  5.1 Expand registry
  5.2 Capability metadata
  5.3 Discovery

Phase 6: Permissions ─────────────────────── Week 4
  6.1 Permission types
  6.2 Tool declaration
  6.3 PermissionChecker

Phase 7: Plugin Runtime ──────────────────── Week 4-5
  7.1 Manifest
  7.2 Runtime
  7.3 API

Phase 8: Gateway + CLI ──────────────────── Week 5
  8.1 Fix Gateway
  8.2 CLI/SDK
```

---

## Immediate Next Steps (start now)

1. **Fix `.gitignore`** — Add vendor/, .ruff_cache/, .pytest_cache/, .env, node_modules/
2. **Remove vendor/ from git tracking** — `git rm -r --cached vendor/`
3. **Fix InferenceEngine ABC** — Add CompletionResult, Usage, StreamChunk
4. **Fix ReActAgent type mismatch** — Use CompletionResult
5. **Create `packages/providers/`** — Package structure
6. **Implement OllamaEngine** — First real provider
7. **Implement OpenAIEngine** — Second provider
8. **Write provider tests** — Mock HTTP, verify parsing
9. **Fix Gateway stub** — Wire to orchestrator
10. **Run full test suite** — Everything passes

---

## Files to modify (immediate)

| File | Change |
|---|---|
| `.gitignore` | Add vendor/, caches, .env, node_modules |
| `packages/agents/src/aios/agents/engine.py` | Add CompletionResult, Usage, StreamChunk; fix return types |
| `packages/agents/src/aios/agents/types.py` | Add StreamChunk, CompletionResult (or keep in engine.py) |
| `packages/agents/src/aios/agents/react/agent.py` | Use CompletionResult |
| `services/gateway/src/aios/gateway/main.py` | Wire /chat to orchestrator |
| `pyproject.toml` | Add packages/providers/ workspace member |
| NEW: `packages/providers/pyproject.toml` | Package config |
| NEW: `packages/providers/src/aios/providers/__init__.py` | Exports |
| NEW: `packages/providers/src/aios/providers/ollama.py` | Ollama adapter |
| NEW: `packages/providers/src/aios/providers/openai.py` | OpenAI adapter |
| NEW: `packages/providers/src/aios/providers/anthropic.py` | Anthropic adapter |
| NEW: `packages/providers/src/aios/providers/litellm.py` | LiteLLM adapter |
| NEW: `packages/providers/src/aios/providers/factory.py` | Engine factory |
| NEW: `tests/test_providers.py` | Provider tests |
| NEW: `tests/test_context.py` | Context engine tests |

---

## Success Criteria (end of M1)

- [ ] 150+ tests passing
- [ ] InferenceEngine ABC returns CompletionResult
- [ ] Ollama adapter works end-to-end (real Ollama if available)
- [ ] OpenAI adapter works end-to-end (mock tests)
- [ ] ContextBuilder assembles context from memory + conversation
- [ ] ReActAgent works with any provider via factory
- [ ] Gateway /chat endpoint works
- [ ] `aios chat "hello"` works from CLI
- [ ] 0 lint errors
- [ ] vendor/ not in git
