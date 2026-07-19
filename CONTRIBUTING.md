# Contributing to AIOS

Thank you for your interest in contributing to AIOS! This document provides guidelines and information about contributing to this project.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, please include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Any relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome. Please provide:

- A clear and descriptive title
- A detailed description of the proposed enhancement
- Any relevant examples or use cases
- Why this enhancement would be useful

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Ensure your code follows the project's style guidelines
5. Add or update tests as needed
6. Update documentation if necessary
7. Commit your changes with a descriptive message
8. Push to your fork and submit a pull request

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+ (for pnpm workspace)
- pnpm 9+
- uv (Python package manager)

### Getting Started

```bash
# Clone the repository
git clone https://github.com/vimarshakk/aios.git
cd aios

# Install Python dependencies
uv sync

# Install Node dependencies (for UI packages)
pnpm install

# Install pre-commit hooks
uv run pre-commit install
```

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

## Style Guidelines

### Python Style

- Follow PEP 8 style guidelines
- Use Ruff for linting and formatting
- Maintain type hints throughout the codebase
- Use docstrings for all public APIs (Google style)

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes (no code change)
- `refactor:` for code refactoring
- `test:` for adding or updating tests
- `chore:` for maintenance tasks
- `ci:` for CI/CD changes

Examples:
```
feat: add vector search to memory system
fix: resolve session state leak in orchestrator
docs: update API reference for gateway endpoints
test: add integration tests for multi-agent routing
```

### Code Organization

- Keep functions focused and small
- Use meaningful variable and function names
- Avoid global state when possible
- Write modular, testable code
- Follow the existing code patterns in each package

## Project Structure

### Core Packages

- `packages/agents/` — Agent framework
- `packages/memory/` — Memory system
- `packages/context/` — Context engine
- `packages/core/` — Shared utilities
- `packages/tools/` — Tool registry
- `packages/voice/` — Voice I/O
- `packages/security/` — Authentication
- `packages/telemetry/` — Metrics
- `packages/plugins/` — Plugin system
- `packages/providers/` — Inference adapters
- `packages/scheduler/` — Task scheduling
- `packages/sdk/` — Client and CLI
- `packages/workflows/` — Workflow engine

### Services

- `services/gateway/` — API gateway
- `services/orchestrator/` — Query routing
- `services/mcp/` — MCP server
- `services/search/` — Search service
- `services/telemetry/` — Telemetry service
- `services/vector/` — Vector store

### Apps

- `apps/desktop/` — Desktop app
- `apps/web/` — Web app
- `apps/mobile/` — Mobile app
- `apps/server/` — Server app

## Testing

### Writing Tests

- Write unit tests for all new functionality
- Write integration tests for complex features
- Aim for high test coverage
- Use meaningful test names that describe the behavior being tested

### Test Organization

- Unit tests go in `tests/unit/`
- Integration tests go in `tests/integration/`
- E2E tests go in `tests/e2e/`

## Documentation

- Update README.md if adding new features
- Add docstrings to all public APIs
- Update any relevant ADRs in `docs/adr/`
- Keep CHANGELOG.md updated with your changes

## Questions?

If you have questions about contributing, feel free to open an issue with the "question" label or reach out to the maintainers.

Thank you for contributing to AIOS!
