.PHONY: help install lint format test test-cov build clean sync check

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Install all packages in dev mode
	uv sync --all-packages -p 3.12

sync:  ## Sync workspace dependencies
	uv sync --all-packages -p 3.12

lint:  ## Run ruff linter
	uv run --with ruff ruff check .

format:  ## Format code with ruff
	uv run --with ruff ruff format .
	uv run --with ruff ruff check --fix .

test:  ## Run all tests
	uv run pytest tests/ -q --tb=short

test-verbose:  ## Run all tests with verbose output
	uv run pytest tests/ -v --tb=short

test-cov:  ## Run tests with coverage report
	uv run pytest tests/ -q --tb=short --cov=packages --cov=services --cov-report=term-missing

build:  ## Build distribution packages
	uv build

clean:  ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml

check:  ## Run all checks (lint + test)
	$(MAKE) lint
	$(MAKE) test

version:  ## Show version info
	@python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"

gateway:  ## Start the gateway server
	uv run python -m aios.gateway.main

orchestrator:  ## Start the orchestrator service
	uv run python -m aios.orchestrator.main
