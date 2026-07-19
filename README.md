# AIOS — AI Operating System

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/vimarshakk/aios/actions/workflows/ci.yml/badge.svg)](https://github.com/vimarshakk/aios/actions)

A personal AI runtime with agents, memory, tools, workflows, plugins, and multi-agent orchestration.

## Overview

AIOS is a modular, extensible AI operating system that provides:

- **Agent Framework** — Base agents with ReAct loop, tool calling, events, permissions, and multi-agent execution
- **Memory System** — Persistent and ephemeral memory with vector search and summarization
- **Context Engine** — Rich context building, retrieval, ranking, and conversation windowing
- **Workflow Engine** — Serial/parallel execution, conditions, approvals, retries, and validation
- **Plugin System** — Dynamic installation, sandboxing, marketplace, and dependency resolution
- **Provider Adapters** — Inference engine adapters (OpenAI, Anthropic, Ollama, etc.)
- **Scheduler** — Task scheduling with cron and one-shot support
- **Gateway Service** — FastAPI REST + WebSocket API for desktop and web UIs
- **Orchestrator** — Central query router with single and multi-agent modes
- **SDK** — Python client and CLI for interacting with the gateway

## Architecture

```
aios/
├── packages/              # Core Python packages (monorepo)
│   ├── agents/            # Agent framework (ReAct, tools, events, pool)
│   ├── memory/            # Persistent and ephemeral memory
│   ├── context/           # Context building, retrieval, ranking
│   ├── core/              # Shared types and utilities
│   ├── tools/             # Tool registry and built-in tools
│   ├── voice/             # Voice input/output
│   ├── security/          # Authentication and authorization
│   ├── telemetry/         # Metrics and tracing
│   ├── plugins/           # Plugin runtime, marketplace, sandbox
│   ├── providers/         # Inference engine adapters
│   ├── scheduler/         # Task scheduling
│   ├── sdk/               # Python client and CLI
│   └── workflows/         # Workflow engine (serial, parallel, conditions)
├── services/              # Infrastructure services
│   ├── gateway/           # FastAPI REST + WebSocket API
│   ├── orchestrator/      # Query routing and session management
│   ├── mcp/               # Model Context Protocol server
│   ├── search/            # Search service
│   ├── telemetry/         # Telemetry service
│   └── vector/            # Vector store service
├── apps/                  # Application surfaces
│   ├── desktop/           # Desktop app (Electron)
│   ├── web/               # Web app (Next.js)
│   ├── mobile/            # Mobile app (React Native)
│   └── server/            # Server app (Docker)
├── vendor/                # Third-party OSS dependencies (gitignored)
├── tests/                 # Test suite
└── docs/                  # Documentation and ADRs
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for pnpm workspace)
- pnpm 9+

### Installation

```bash
# Clone the repository
git clone https://github.com/vimarshakk/aios.git
cd aios

# Install Python dependencies
uv sync

# Install Node dependencies (for UI packages)
pnpm install
```

### Running the Gateway

```bash
# Start the gateway service
uv run aios-gateway

# Or run directly
uv run python -m aios.gateway.main
```

The gateway starts on `http://localhost:8080` by default.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check with agent and tool info |
| `POST` | `/chat` | Send a message to an agent |
| `GET` | `/agents` | List registered agents |
| `GET` | `/tools` | List registered tools |
| `WS` | `/ws/chat` | WebSocket chat endpoint |

### Example: Chat with an Agent

```python
from aios.sdk import AiosClient

client = AiosClient("http://localhost:8080")
response = client.chat("Hello, what can you do?")
print(response)
```

### Example: Use the Orchestrator Directly

```python
from aios.orchestrator import Orchestrator
from aios.agents import ReActAgent

orchestrator = Orchestrator()

# Register an agent
agent = ReActAgent(name="assistant", model="gpt-4")
orchestrator.register_agent("assistant", agent, capabilities={"general", "coding"})

# Route a query
response = await orchestrator.route("Write a Python function to sort a list")
print(response)
```

### Example: Multi-Agent Orchestration

```python
from aios.orchestrator import Orchestrator

orchestrator = Orchestrator()

# Register agents with capabilities
orchestrator.register_agent("coder", coder_agent, capabilities={"coding", "python"})
orchestrator.register_agent("researcher", researcher_agent, capabilities={"search", "analysis"})
orchestrator.register_agent("writer", writer_agent, capabilities={"writing", "editing"})

# Multi-agent mode: decompose → execute → aggregate
response = await orchestrator.route(
    "Research Python async patterns, write a tutorial, and review it for errors",
    mode="multi",
)
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=aios --cov-report=html

# Run specific package tests
uv run pytest packages/agents/tests/
```

### Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run pyright
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run all hooks manually
uv run pre-commit run --all-files
```

## Project Structure

### Core Packages

| Package | Description |
|---------|-------------|
| `agents` | Agent framework with ReAct loop, tools, events, permissions |
| `memory` | Persistent and ephemeral memory with vector search |
| `context` | Context building, retrieval, ranking, and summarization |
| `core` | Shared types, utilities, and base classes |
| `tools` | Tool registry and built-in tools |
| `voice` | Voice input/output processing |
| `security` | Authentication and authorization |
| `telemetry` | Metrics, tracing, and logging |
| `plugins` | Plugin runtime, marketplace, sandbox, dependency resolution |
| `providers` | Inference engine adapters (OpenAI, Anthropic, Ollama) |
| `scheduler` | Task scheduling with cron and one-shot support |
| `sdk` | Python client and CLI |
| `workflows` | Workflow engine with serial/parallel execution |

### Services

| Service | Description |
|---------|-------------|
| `gateway` | FastAPI REST + WebSocket API |
| `orchestrator` | Central query router and session manager |
| `mcp` | Model Context Protocol server |
| `search` | Search service |
| `telemetry` | Telemetry collection service |
| `vector` | Vector store service |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to AIOS.

## Security

See [SECURITY.md](SECURITY.md) for reporting security vulnerabilities.

## License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.
