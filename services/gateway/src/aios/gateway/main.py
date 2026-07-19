"""AIOS Gateway — FastAPI application entry point.

Provides REST + WebSocket + SSE streaming endpoints for desktop and web UIs.

Endpoints:
    GET  /health              — Health check
    GET  /models              — Available models and providers
    GET  /agents              — Registered agents with capabilities
    GET  /tools               — Registered tools
    POST /chat                — Chat (single/multi agent)
    GET  /chat/stream         — SSE streaming chat
    WS   /ws/chat             — WebSocket chat
    POST /tts                 — Text-to-speech (macOS say / browser fallback)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from aios.agents import EventType, get_event_bus
from aios.agents.registry import AgentRegistry, ToolRegistry
from aios.agents.specialized.browser_agent import BrowserAgent
from aios.agents.specialized.coding_agent import CodingAgent
from aios.agents.specialized.memory_agent import MemoryAgent
from aios.agents.specialized.research_agent import ResearchAgent
from aios.agents.specialized.vision_agent import VisionAgent
from aios.orchestrator.main import Orchestrator
from aios.platform import DeveloperPlatform
from aios.providers.factory import auto_select_engine, list_models
from aios.supervisor import Daemon, Supervisor
from aios.tools.builtin import ALL_BUILTIN_TOOLS

logger = logging.getLogger("aios.gateway")

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    agent: str | None = None
    session_id: str | None = None
    context: dict[str, Any] | None = None
    mode: str = "single"  # "single" | "multi"
    model: str | None = None  # Override model for this request


class ChatResponse(BaseModel):
    response: str
    agent: str
    session_id: str
    usage: dict[str, Any] | None = None
    model: str | None = None


class ToolInfo(BaseModel):
    name: str
    description: str
    category: str


class AgentInfo(BaseModel):
    name: str
    type: str
    capabilities: list[str] = []
    description: str = ""
    model: str = ""


class ModelInfo(BaseModel):
    id: str
    provider: str
    description: str


class HealthResponse(BaseModel):
    status: str
    version: str
    agents: list[str]
    tools: list[str]
    providers: list[str]


class TTSRequest(BaseModel):
    text: str
    voice: str = "Samantha"  # macOS voice


# ---------------------------------------------------------------------------
# Global orchestrator
# ---------------------------------------------------------------------------

_orchestrator: Orchestrator | None = None
_platform: DeveloperPlatform | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def get_platform() -> DeveloperPlatform:
    """Return the shared Developer Platform runtime (catalog + policy + skills)."""
    global _platform
    if _platform is None:
        _platform = DeveloperPlatform(
            encryptor_password=os.environ.get("AIOS_VAULT_PASSWORD", "dev-platform")
        )
        _platform.bootstrap()
    return _platform


# ---------------------------------------------------------------------------
# Agent factory — create and register all specialized agents
# ---------------------------------------------------------------------------

_AGENT_CONFIGS = [
    {
        "name": "default",
        "task_type": "default",
        "cls": None,  # Uses ReAct agent
        "capabilities": {"general", "chat", "reasoning"},
        "description": "General-purpose assistant for any task.",
    },
    {
        "name": "research",
        "task_type": "research",
        "cls": ResearchAgent,
        "capabilities": {"research", "web_search", "synthesis"},
        "description": "Searches the web and synthesizes research reports.",
    },
    {
        "name": "coding",
        "task_type": "coding",
        "cls": CodingAgent,
        "capabilities": {"coding", "shell_execution", "debugging"},
        "description": "Writes and executes code. Powered by Open Interpreter patterns.",
    },
    {
        "name": "browser",
        "task_type": "default",
        "cls": BrowserAgent,
        "capabilities": {"browser", "web_automation", "scraping"},
        "description": "Automates web browsers with Playwright.",
    },
    {
        "name": "memory",
        "task_type": "default",
        "cls": MemoryAgent,
        "capabilities": {"memory", "knowledge", "notes"},
        "description": "Stores and retrieves information from your personal memory.",
    },
    {
        "name": "vision",
        "task_type": "vision",
        "cls": VisionAgent,
        "capabilities": {"vision", "screenshot", "image_analysis"},
        "description": "Analyzes images and screenshots using vision models.",
    },
]


def _get_local_ollama_models() -> list[str]:
    """Retrieve list of installed models from local Ollama service."""
    import httpx
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
    except (httpx.HTTPError, OSError) as exc:
        logger.debug("Ollama model list unavailable: %s", exc)
    return []


def _build_agents(platform: DeveloperPlatform) -> None:
    """Create and register all specialized agents via the Developer Platform.

    Registration indexes each agent's capabilities into the shared
    :class:`CapabilityCatalog` (single source of truth), in addition to the
    orchestrator's routing pool.
    """
    from aios.agents.react.agent import ReActAgent

    local_models = _get_local_ollama_models()
    # Try to find a default local model if standard ones are not present
    fallback_model = "ollama/llama3.2"
    if local_models:
        best_defaults = [
            "llama3.2",
            "qwen3",
            "qwen2.5-coder",
            "qwen2.5",
            "phi3",
            "mistral",
            "llama",
        ]
        matched_best = next(
            (m for d in best_defaults for m in local_models if d in m), None
        )
        if matched_best is not None:
            fallback_model = f"ollama/{matched_best}"
        else:
            fallback_model = f"ollama/{local_models[0]}"

    for cfg in _AGENT_CONFIGS:
        engine = auto_select_engine(cfg["task_type"])
        # Check if the auto-selected model is actually installed locally, otherwise use fallback
        model = getattr(engine, "_default_model", "ollama/llama3.2")
        if model.startswith("ollama/") and local_models:
            model_name = model.split("/", 1)[1]
            if model_name not in local_models and not any(model_name in m for m in local_models):
                model = fallback_model

        cls = cfg.get("cls")
        if cls is None:
            # Default: ReAct agent with all builtin tools
            agent = ReActAgent(engine, model, tools=ALL_BUILTIN_TOOLS)
        elif cls is CodingAgent:
            # Let's customize CodingAgent to default to qwen2.5-coder if available
            coding_model = model
            if "qwen2.5-coder" in "".join(local_models):
                matched_coder = [m for m in local_models if "qwen2.5-coder" in m]
                if matched_coder:
                    coding_model = f"ollama/{matched_coder[0]}"
            agent = cls(engine, coding_model)
        elif cls in (ResearchAgent, BrowserAgent, MemoryAgent, VisionAgent):
            agent = cls(engine, model)
        else:
            agent = cls(engine, model)  # type: ignore[call-arg]

        platform.register_agent(
            cfg["name"],
            agent,
            capability_ids=cfg["capabilities"],
        )

    # Register all builtin tools
    for tool in ALL_BUILTIN_TOOLS:
        ToolRegistry.register_value(tool.spec.name, tool.describe())


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bus = get_event_bus(record_history=True)
    platform = get_platform()
    _build_agents(platform)
    bus.publish(EventType.SESSION_START, {"service": "gateway", "agents": len(_AGENT_CONFIGS)})
    yield
    bus.publish(EventType.SESSION_END, {"service": "gateway"})


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AIOS Gateway",
    version="0.3.0",
    description="AIOS — AI Operating System. Multi-agent, multi-model, voice-first.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    agents = [name for name, _ in AgentRegistry.items()]
    tools = [name for name, _ in ToolRegistry.items()]
    return HealthResponse(
        status="ok",
        version="0.3.0",
        agents=agents,
        tools=tools,
        providers=["litellm", "ollama", "openai", "anthropic", "openrouter"],
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@app.get("/models", response_model=list[ModelInfo])
async def list_available_models() -> list[ModelInfo]:
    models_map = list_models()
    result = [
        ModelInfo(
            id="ollama/llama3.2",
            provider="ollama",
            description="Llama 3.2 — fast local model",
        ),
        ModelInfo(
            id="ollama/codellama",
            provider="ollama",
            description="Code Llama — coding specialist",
        ),
        ModelInfo(
            id="ollama/llava",
            provider="ollama",
            description="LLaVA — vision + text (local)",
        ),
        ModelInfo(
            id="ollama/mistral",
            provider="ollama",
            description="Mistral 7B — balanced local",
        ),
        ModelInfo(
            id="ollama/phi3",
            provider="ollama",
            description="Phi-3 — small, fast, capable",
        ),
        ModelInfo(
            id="ollama/deepseek-coder",
            provider="ollama",
            description="DeepSeek Coder — coding",
        ),
        ModelInfo(
            id="ollama/qwen2.5",
            provider="ollama",
            description="Qwen 2.5 — multilingual",
        ),
        ModelInfo(
            id="gpt-4o",
            provider="openai",
            description="GPT-4o — flagship OpenAI",
        ),
        ModelInfo(
            id="gpt-4o-mini",
            provider="openai",
            description="GPT-4o mini — fast + cheap",
        ),
        ModelInfo(
            id="claude-3-5-sonnet-20241022",
            provider="anthropic",
            description="Claude 3.5 Sonnet — best reasoning",
        ),
        ModelInfo(
            id="claude-3-haiku-20240307",
            provider="anthropic",
            description="Claude 3 Haiku — ultra fast",
        ),
        ModelInfo(
            id="gemini/gemini-1.5-pro",
            provider="gemini",
            description="Gemini 1.5 Pro — multimodal",
        ),
        ModelInfo(
            id="gemini/gemini-1.5-flash",
            provider="gemini",
            description="Gemini 1.5 Flash — fast",
        ),
        ModelInfo(
            id="openrouter/meta-llama/llama-3.1-8b-instruct",
            provider="openrouter",
            description="Llama 3.1 8B via OpenRouter",
        ),
    ]

    # Query Ollama dynamically for local models
    import httpx
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                for t in tags:
                    name = t.get("name")
                    if name:
                        model_id = f"ollama/{name}"
                        if not any(m.id == model_id for m in result):
                            result.append(
                                ModelInfo(
                                    id=model_id,
                                    provider="ollama",
                                    description=f"Local model: {name}",
                                )
                            )
    except (httpx.HTTPError, OSError) as exc:
        logger.debug("Ollama model list unavailable: %s", exc)

    # Add task defaults
    for task, model in models_map.items():
        if not any(m.id == model for m in result):
            result.append(
                ModelInfo(id=model, provider="auto", description=f"Auto-selected for {task}")
            )
    return result


# ---------------------------------------------------------------------------
# Agents + Tools
# ---------------------------------------------------------------------------


@app.get("/agents", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    orch = get_orchestrator()
    result = []
    for cfg in _AGENT_CONFIGS:
        agent = orch._agents.get(cfg["name"])  # noqa: SLF001
        model = getattr(agent, "_model", "") if agent else ""
        result.append(AgentInfo(
            name=cfg["name"],
            type=cfg["cls"].__name__ if cfg["cls"] else "ReActAgent",
            capabilities=sorted(cfg["capabilities"]),
            description=cfg["description"],
            model=model,
        ))
    return result


@app.get("/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    return [
        ToolInfo(name=t.spec.name, description=t.spec.description, category=t.spec.category)
        for t in ALL_BUILTIN_TOOLS
    ]


@app.get("/capabilities")
async def list_capabilities() -> dict[str, object]:
    """List the platform capability catalog (single source of truth)."""
    platform = get_platform()
    nodes = platform.catalog.all()
    return {
        "count": len(nodes),
        "capabilities": [
            {
                "name": n.name,
                "description": n.description,
                "scope": n.scope.value,
                "parent": n.parent,
                "tags": list(n.tags),
            }
            for n in nodes
        ],
    }


# ---------------------------------------------------------------------------
# Chat — single + multi-agent
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    orchestrator = get_orchestrator()

    # Override model if specified
    if req.model and req.agent:
        agent = orchestrator._agents.get(req.agent)  # noqa: SLF001
        if agent and hasattr(agent, "_model"):
            agent._model = req.model  # type: ignore[assignment]  # noqa: SLF001

    response_text = await orchestrator.route(
        query=req.message,
        session_id=req.session_id,
        agent_name=req.agent,
        mode=req.mode,
    )

    session = orchestrator.get_or_create_session(req.session_id)

    return ChatResponse(
        response=response_text,
        agent=session.agent_name,
        session_id=session.id,
        model=req.model,
    )


# ---------------------------------------------------------------------------
# SSE Streaming Chat
# ---------------------------------------------------------------------------


@app.get("/chat/stream")
async def chat_stream(
    message: str = Query(..., description="Message to send"),
    agent: str = Query(default="default", description="Agent name"),
    session_id: str | None = Query(default=None, description="Session ID"),
    model: str | None = Query(default=None, description="Model override"),
) -> StreamingResponse:
    """Server-Sent Events streaming chat endpoint."""

    async def generate():
        orchestrator = get_orchestrator()

        # Try to get a streaming-capable agent
        agent_obj = orchestrator._agents.get(agent)  # noqa: SLF001
        if agent_obj is None:
            yield f"data: {json.dumps({'error': f'Agent {agent!r} not found'})}\n\n"
            return

        # Get engine for streaming
        engine = getattr(agent_obj, "_engine", None)
        agent_model = model or getattr(agent_obj, "_model", "ollama/llama3.2")

        if engine is None or not hasattr(engine, "stream"):
            # Fallback: non-streaming
            response = await orchestrator.route(
                query=message,
                session_id=session_id,
                agent_name=agent,
            )
            # Send as single chunk
            for i in range(0, len(response), 50):
                chunk = response[i:i + 50]
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            return

        from aios.agents.types import Message, Role
        messages = [
            Message(role=Role.SYSTEM, content="You are AIOS, a helpful AI assistant."),
            Message(role=Role.USER, content=message),
        ]

        try:
            async for chunk in engine.stream(messages, model=agent_model):
                if chunk.content:
                    yield f"data: {json.dumps({'content': chunk.content, 'done': chunk.done})}\n\n"
                if chunk.done:
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    break
        except (ValueError, RuntimeError, OSError) as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# WebSocket Chat
# ---------------------------------------------------------------------------


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    orchestrator = get_orchestrator()
    session_id = "ws_default"
    try:
        while True:
            data = await websocket.receive_json()
            msg = data.get("message", "")
            agent_name = data.get("agent", "default")
            mode = data.get("mode", "single")

            response_text = await orchestrator.route(
                query=msg,
                session_id=session_id,
                agent_name=agent_name,
                mode=mode,
            )

            await websocket.send_json({
                "response": response_text,
                "agent": agent_name,
                "session_id": session_id,
            })
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# TTS — macOS say command / browser fallback
# ---------------------------------------------------------------------------


@app.post("/tts")
async def text_to_speech(req: TTSRequest) -> dict[str, str]:
    """Convert text to speech using macOS 'say' command."""
    import platform

    if platform.system() != "Darwin":
        return {
            "status": "use_browser",
            "message": "TTS only available on macOS server-side. Use browser SpeechSynthesis.",
        }

    try:
        # Run macOS say command asynchronously
        proc = await asyncio.create_subprocess_exec(
            "say", "-v", req.voice, req.text[:500],  # cap at 500 chars
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=30)
    except (OSError, TimeoutError) as e:
        return {"status": "error", "message": str(e)}
    else:
        return {"status": "ok", "voice": req.voice}


# ---------------------------------------------------------------------------
# Supervisor — single execution interface for autonomous goals (M5.1)
# ---------------------------------------------------------------------------


_supervisor: Supervisor | None = None


def get_supervisor() -> Supervisor:
    """Return the shared Supervisor, composed over the shared platform."""
    global _supervisor
    if _supervisor is None:
        _supervisor = Supervisor(get_platform())
    return _supervisor


class GoalRequest(BaseModel):
    objective: str
    capabilities: list[str] | None = None
    metadata: dict[str, Any] | None = None


class GoalActionResponse(BaseModel):
    goal_id: str
    status: str


@app.post("/goals", response_model=GoalActionResponse)
async def create_goal(req: GoalRequest) -> GoalActionResponse:
    """Submit a new goal; planning + execution begin immediately."""
    sup = get_supervisor()
    goal = await sup.submit(req.objective, capabilities=req.capabilities, metadata=req.metadata)
    return GoalActionResponse(goal_id=goal.goal_id, status=goal.status.value)


@app.get("/goals")
async def list_goals() -> list[dict[str, Any]]:
    """List all tracked goals with their progress."""
    return get_supervisor().list_goals()


@app.get("/goals/{goal_id}")
async def get_goal(goal_id: str) -> dict[str, Any]:
    """Get a single goal's full state, or 404 if unknown."""
    goal = get_supervisor().get_goal(goal_id)
    if goal is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"unknown goal: {goal_id}")
    return goal.to_dict()


@app.post("/goals/{goal_id}/pause", response_model=GoalActionResponse)
async def pause_goal(goal_id: str) -> GoalActionResponse:
    await get_supervisor().pause(goal_id)
    goal = get_supervisor().get_goal(goal_id)
    return GoalActionResponse(goal_id=goal_id, status=goal.status.value if goal else "unknown")


@app.post("/goals/{goal_id}/resume", response_model=GoalActionResponse)
async def resume_goal(goal_id: str) -> GoalActionResponse:
    await get_supervisor().resume(goal_id)
    goal = get_supervisor().get_goal(goal_id)
    return GoalActionResponse(goal_id=goal_id, status=goal.status.value if goal else "unknown")


@app.post("/goals/{goal_id}/cancel", response_model=GoalActionResponse)
async def cancel_goal(goal_id: str) -> GoalActionResponse:
    await get_supervisor().cancel(goal_id)
    goal = get_supervisor().get_goal(goal_id)
    return GoalActionResponse(goal_id=goal_id, status=goal.status.value if goal else "unknown")


@app.websocket("/goals/{goal_id}/events")
async def goal_events(websocket: WebSocket) -> None:
    """Stream a goal's progress as it executes (live status + steps)."""
    await websocket.accept()
    goal_id = websocket.path_params["goal_id"]
    sup = get_supervisor()
    last_seen = ""
    try:
        while True:
            goal = sup.get_goal(goal_id)
            if goal is None:
                await websocket.send_json({"error": f"unknown goal: {goal_id}"})
                break
            snapshot = goal.to_dict()
            if snapshot != last_seen:
                await websocket.send_json(snapshot)
                last_seen = snapshot
            if goal.is_terminal:
                break
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
    finally:
        with contextlib.suppress(RuntimeError):
            await websocket.close()


@app.websocket("/goals/ws")
async def goals_stream(websocket: WebSocket) -> None:
    """Single global event stream for *all* goals.

    Emits a snapshot of every tracked goal whenever any goal's state changes.
    Suitable for a live dashboard / multi-goal viewer (Priority 1 of the
    external-control surface).
    """
    await websocket.accept()
    sup = get_supervisor()
    last_fingerprint = ""
    try:
        # Initial full snapshot so a fresh client sees current state immediately.
        await websocket.send_json({"type": "snapshot", "goals": sup.list_goals()})
        while True:
            goals = sup.list_goals()
            # Fingerprint on status + event count to detect any change cheaply.
            fingerprint = "|".join(
                f"{g['goal_id']}:{g['status']}:{len(g.get('events', []))}" for g in goals
            )
            if fingerprint != last_fingerprint:
                last_fingerprint = fingerprint
                await websocket.send_json({"type": "snapshot", "goals": goals})
                # Once every tracked goal has reached a terminal state, emit a
                # done frame and close so followers (dashboards / tests) exit
                # cleanly instead of polling forever.
                terminal = {"completed", "failed", "cancelled"}
                if goals and all(g["status"] in terminal for g in goals):
                    await websocket.send_json({"type": "done"})
                    break
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
    finally:
        with contextlib.suppress(RuntimeError):
            await websocket.close()


# ---------------------------------------------------------------------------
# M5.3 / M5.5 — AIOS daemon host + proactive briefing
# ---------------------------------------------------------------------------

_daemon: Daemon | None = None


def get_daemon() -> Daemon:
    """Return the shared AIOS daemon (hosts the Supervisor + scheduler)."""
    global _daemon
    if _daemon is None:
        from aios.supervisor import BriefingConfig, BriefingEngine, Daemon, DaemonConfig

        platform = get_platform()
        briefing = BriefingEngine(platform=platform, config=BriefingConfig())
        _daemon = Daemon(platform, DaemonConfig(briefing=briefing))
    return _daemon


@app.get("/daemon/status")
async def daemon_status() -> dict[str, object]:
    """Report daemon uptime, goal count, and briefing enablement."""
    return get_daemon().status()


class BriefingTriggerResponse(BaseModel):
    scheduled: bool
    objective: str | None = None


@app.post("/briefing/trigger", response_model=BriefingTriggerResponse)
async def briefing_trigger() -> BriefingTriggerResponse:
    """Compose (and optionally schedule) today's proactive briefing goal."""
    from aios.supervisor import BriefingConfig, BriefingEngine

    daemon = get_daemon()
    engine = daemon.config.briefing or BriefingEngine(
        platform=get_platform(), config=BriefingConfig()
    )
    objective = engine.compose_objective()
    if objective is None:
        return BriefingTriggerResponse(scheduled=False)
    goal_id = await daemon.submit(objective, metadata={"kind": "briefing"})
    engine.mark_run(goal_id)
    return BriefingTriggerResponse(scheduled=True, objective=objective)


# ---------------------------------------------------------------------------
# M17 — Workforce / CLI / Review endpoints
# ---------------------------------------------------------------------------

# In-memory workforce store (mirrors desktop WorkforceManager for web-only mode)
_DEFAULT_WORKFORCE_ROLES: list[dict[str, Any]] = [
    {"id": "architect", "role": "architect", "capabilities": ["architecture", "system-design", "planning"], "status": "idle"},
    {"id": "backend", "role": "backend", "capabilities": ["coding", "api-design", "databases"], "status": "idle"},
    {"id": "frontend", "role": "frontend", "capabilities": ["coding", "ui", "css", "react"], "status": "idle"},
    {"id": "qa", "role": "qa", "capabilities": ["testing", "qa", "automation"], "status": "idle"},
    {"id": "devops", "role": "devops", "capabilities": ["deployment", "ci-cd", "infrastructure"], "status": "idle"},
    {"id": "researcher", "role": "researcher", "capabilities": ["research", "web-search", "analysis"], "status": "idle"},
    {"id": "designer", "role": "designer", "capabilities": ["design", "ui-ux", "figma"], "status": "idle"},
    {"id": "reviewer", "role": "reviewer", "capabilities": ["code-review", "quality", "security"], "status": "idle"},
]

_workforce_store: list[dict[str, Any]] = list(_DEFAULT_WORKFORCE_ROLES)
_review_store: list[dict[str, Any]] = []


@app.get("/workforce/workers")
async def workforce_list_workers() -> list[dict[str, Any]]:
    """List all registered workers in the workforce."""
    return list(_workforce_store)


@app.get("/workforce/workers/{worker_id}")
async def workforce_get_worker(worker_id: str) -> dict[str, Any]:
    """Get a single worker by ID."""
    for w in _workforce_store:
        if w["id"] == worker_id:
            return w
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"worker {worker_id!r} not found")


@app.get("/workforce/capability/{capability}")
async def workforce_find_by_capability(capability: str) -> list[dict[str, Any]]:
    """Find workers that have a given capability."""
    return [w for w in _workforce_store if capability in w.get("capabilities", [])]


@app.post("/workforce/assign")
async def workforce_assign_task(body: dict[str, Any]) -> dict[str, Any]:
    """Assign a task to a worker."""
    worker_id = body.get("worker_id", "")
    for w in _workforce_store:
        if w["id"] == worker_id:
            w["status"] = "busy"
            return {"ok": True, "worker_id": worker_id, "task": body.get("task", "")}
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"worker {worker_id!r} not found")


@app.post("/workforce/complete")
async def workforce_complete_task(body: dict[str, Any]) -> dict[str, Any]:
    """Mark a worker's task as complete."""
    worker_id = body.get("worker_id", "")
    for w in _workforce_store:
        if w["id"] == worker_id:
            w["status"] = "idle"
            return {"ok": True, "worker_id": worker_id}
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"worker {worker_id!r} not found")


@app.post("/workforce/fail")
async def workforce_fail_task(body: dict[str, Any]) -> dict[str, Any]:
    """Mark a worker's task as failed."""
    worker_id = body.get("worker_id", "")
    for w in _workforce_store:
        if w["id"] == worker_id:
            w["status"] = "error"
            return {"ok": True, "worker_id": worker_id}
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"worker {worker_id!r} not found")


@app.get("/workforce/state")
async def workforce_state() -> dict[str, Any]:
    """Get full workforce state."""
    return {"workers": list(_workforce_store), "count": len(_workforce_store)}


@app.get("/cli/active")
async def cli_active() -> list[dict[str, Any]]:
    """List active CLI processes."""
    return []


@app.post("/cli/spawn")
async def cli_spawn(body: dict[str, Any]) -> dict[str, Any]:
    """Spawn a new CLI process."""
    return {"ok": True, "pid": 0, "message": "CLI spawn simulated in web mode"}


@app.get("/review/active")
async def review_active() -> list[dict[str, Any]]:
    """List active reviews."""
    return [r for r in _review_store if r.get("status") != "approved"]


@app.post("/review/create")
async def review_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new review request."""
    import uuid
    review = {
        "id": str(uuid.uuid4()),
        "title": body.get("title", "Untitled Review"),
        "description": body.get("description", ""),
        "status": "pending",
        "verdict": None,
        "rounds": 0,
        "notes": [],
    }
    _review_store.append(review)
    return review


@app.post("/review/{review_id}/verdict")
async def review_submit_verdict(review_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Submit a verdict on a review."""
    for r in _review_store:
        if r["id"] == review_id:
            r["verdict"] = body.get("verdict", "approved")
            r["status"] = body.get("verdict", "approved")
            return r
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"review {review_id!r} not found")


@app.get("/review/state")
async def review_state() -> dict[str, Any]:
    """Get full review state."""
    return {"reviews": list(_review_store), "count": len(_review_store)}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run() -> None:
    import uvicorn
    port = int(os.environ.get("AIOS_GATEWAY_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)  # noqa: S104


__all__ = ["app", "get_daemon", "get_supervisor", "run"]
