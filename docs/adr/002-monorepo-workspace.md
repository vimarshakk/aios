# ADR 002: Monorepo with Python Workspace

## Status

Accepted

## Context

AIOS consists of multiple packages (agents, memory, context, etc.) and services. We need to decide how to organize these.

Options:
1. Multiple separate repositories
2. Monorepo with a single package
3. Monorepo with workspace packages

## Decision

We will use a monorepo with Python workspace packages using `uv` workspaces.

## Consequences

### Positive

- Shared code and types across packages
- Atomic commits across related changes
- Simplified dependency management
- Easy cross-package refactoring
- Single CI/CD pipeline

### Negative

- Larger repository size
- More complex build configuration
- Potential for circular dependencies

### Mitigations

- Use clear package boundaries
- Enforce dependency direction (core → agents → services)
- Regular dependency audits
- Use `uv` for fast, reliable dependency management
