# ADR 003: Use FastAPI for Gateway Service

## Status

Accepted

## Context

AIOS needs an API gateway to expose REST and WebSocket endpoints for desktop and web UIs.

Options:
1. Flask
2. Django
3. FastAPI
4. Starlette
5. Custom WSGI/ASGI server

## Decision

We will use FastAPI for the gateway service.

## Consequences

### Positive

- Native async/await support
- Automatic OpenAPI documentation
- Pydantic integration for request/response validation
- WebSocket support out of the box
- High performance (comparable to Go/Node.js)
- Type-safe API design

### Negative

- Smaller ecosystem than Flask/Django
- Newer, less battle-tested
- Learning curve for team members unfamiliar with it

### Mitigations

- Extensive documentation and examples
- Use Pydantic for all data models
- Leverage auto-generated OpenAPI docs
