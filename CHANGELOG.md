# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.14.1] - 2026-07-20

### Fixed
- Next.js 16 / Turbopack production build now compiles cleanly (TypeScript check passes)
- Added missing frontend API client methods referenced by legacy workspace components:
  `streamChat`, `createGoal`, `listGoals`, `subscribeAllGoals`, `pauseGoal`/`resumeGoal`/`cancelGoal`,
  `recentMemory`/`searchMemory`/`rememberMemory`, memory graph/workspace/hybrid-search/export/import stubs,
  `listProjects`/`scanProjects`, and `health`/`tools` backward-compat aliases
- Fixed Lucide icon usage: `MetricCard` now accepts a `LucideIcon` and renders it; `Dock` wraps icons in `<span>`
- Added `SpeechRecognition` ambient DOM types; expanded `VoiceEvent` union and fixed `VoiceClient` API surface
- Repaired `Conversation`, `Goals`, `Memory`, `MemoryExplorer`, `Projects`, `MissionControl`, `Settings`,
  `Agents`, `Skills`, `Logs` against real API/type shapes
- Fixed `registry.tsx` component loaders to map named exports (MissionControl, Conversation, Goals, etc.)
  and default exports (M17.2 dedicated workspaces)
- Deleted dead `DevMode.tsx` (superseded by M17.2 dedicated workspace components)
- Updated M17 tests to validate the M17.2 dedicated workspace architecture
- Verified: `npx next build` clean, `pytest` 243 passed

## [0.14.0] - 2026-07-20

### Added
- M17.1: Gateway endpoints (15+), frontend API client, full integration pass — 241 tests passing
- M17.2: Dedicated workspace components replacing monolithic DevModeWorkspace
  - `WorkforceWorkspace` — worker cards, status badges, task graph
  - `RepositoriesWorkspace` — repo cards, search, file count, language badges
  - `ConsolesWorkspace` — terminal sessions with elapsed timer
  - `ReviewsWorkspace` — review cards with approve/reject workflow
- M17.2: `/repositories` and `/repositories/{repo_id}` gateway endpoints
- M17.2: `RepositoryInfo` type in frontend API client

### Added

- Initial project structure and architecture
- Agent framework with ReAct loop and tool calling
- Memory system with persistent and ephemeral storage
- Context engine with retrieval, ranking, and summarization
- Workflow engine with serial/parallel execution
- Plugin system with marketplace and sandboxing
- Provider adapters for OpenAI, Anthropic, and Ollama
- Task scheduler with cron and one-shot support
- Gateway service with REST and WebSocket APIs
- Orchestrator with single and multi-agent routing
- SDK with Python client and CLI
- MCP server for Model Context Protocol
- Vector store service
- Search service
- Telemetry service
- Desktop, web, mobile, and server applications
- Comprehensive test suite
- Documentation and ADRs
- CI/CD with GitHub Actions
- Pre-commit hooks and code quality tools
- Docker support
- Example code and tutorials
