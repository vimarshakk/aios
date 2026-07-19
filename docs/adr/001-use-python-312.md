# ADR 001: Use Python 3.12 as Primary Language

## Status

Accepted

## Context

AIOS needs a primary programming language for its core packages and services. The language should:

- Have strong typing and modern syntax
- Support async/await natively
- Have a rich ecosystem for AI/ML
- Be easy to learn and maintain
- Have good tooling (linting, formatting, testing)

## Decision

We will use Python 3.12 as the primary language for AIOS.

## Consequences

### Positive

- Modern syntax (type hints, match statements, f-strings)
- Excellent async/await support for concurrent operations
- Rich AI/ML ecosystem (OpenAI, Anthropic, Hugging Face)
- Strong typing with mypy/pyright
- Great tooling (Ruff, pytest, pre-commit)

### Negative

- Slower than compiled languages (Go, Rust)
- Global Interpreter Lock (GIL) limits true parallelism
- Memory usage can be higher than alternatives

### Mitigations

- Use multiprocessing for CPU-bound tasks
- Use async I/O for network-bound tasks
- Optimize critical paths with C extensions if needed
