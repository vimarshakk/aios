# ADR 005: Use Ruff for Linting and Formatting

## Status

Accepted

## Context

AIOS needs consistent code style and quality across all packages. We need:

- Fast linting
- Fast formatting
- Configurable rules
- Good IDE integration

Options:
1. Flake8 + Black + isort
2. Ruff
3. Pylint + autopep8
4. Pyflakes + yapf

## Decision

We will use Ruff for linting and formatting.

## Consequences

### Positive

- Extremely fast (written in Rust)
- Single tool for linting and formatting
- Configurable (can replace flake8, isort, pyupgrade, etc.)
- Good IDE integration
- Active development and community

### Negative

- Newer tool, less mature than alternatives
- Some rules may not be as comprehensive as specialized tools
- May need additional tools for specific use cases

### Mitigations

- Use comprehensive rule sets (E, W, F, I, N, UP, B, etc.)
- Add custom rules as needed
- Monitor for new features and improvements
