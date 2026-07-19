"""Engine factory — create inference engines by name.

Supported engines:
    - "litellm":    Universal adapter (Ollama, OpenAI, Claude, Gemini, OpenRouter…)
    - "ollama":     OllamaEngine — local-first, zero config
    - "openai":     OpenAIEngine — needs OPENAI_API_KEY
    - "anthropic":  AnthropicEngine — needs ANTHROPIC_API_KEY
    - "openrouter": OpenRouter — needs OPENROUTER_API_KEY
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from aios.agents.registry import EngineRegistry

if TYPE_CHECKING:
    from aios.agents.engine import InferenceEngine

# Lazy-loaded engine map: name → "module:Class"
_ENGINES: dict[str, str] = {
    "litellm":    "aios.providers.litellm_provider:LiteLLMEngine",
    "ollama":     "aios.providers.ollama:OllamaEngine",
    "openai":     "aios.providers.openai_provider:OpenAIEngine",
    "anthropic":  "aios.providers.anthropic_provider:AnthropicEngine",
    "openrouter": "aios.providers.openrouter_provider:OpenRouterEngine",
}

# Task-type → recommended model (env-overridable)
_TASK_MODELS: dict[str, str] = {
    "coding":    os.environ.get("AIOS_CODING_MODEL",    "ollama/codellama"),
    "vision":    os.environ.get("AIOS_VISION_MODEL",    "ollama/llava"),
    "research":  os.environ.get("AIOS_RESEARCH_MODEL",  "ollama/llama3.2"),
    "fast":      os.environ.get("AIOS_FAST_MODEL",      "ollama/phi3"),
    "reasoning": os.environ.get("AIOS_REASONING_MODEL", "ollama/llama3.1"),
    "default":   os.environ.get("AIOS_DEFAULT_MODEL",   "ollama/llama3.2"),
}


def create_engine(name: str, **kwargs: Any) -> InferenceEngine:
    """Create an inference engine by name.

    Any extra kwargs are forwarded to the engine constructor.

    Raises:
        ValueError: Unknown engine name.
        ImportError: Required SDK not installed.
    """
    # Registry-registered engines take priority
    if EngineRegistry.contains(name):
        entry = EngineRegistry.get(name)
        return entry(**kwargs) if callable(entry) else entry  # type: ignore[return-value]

    # Lazy import from the module map
    if name in _ENGINES:
        import importlib
        module_path, class_name = _ENGINES[name].split(":")
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls(**kwargs)

    available = sorted(set(list(_ENGINES.keys()) + list(EngineRegistry.keys())))
    msg = f"Unknown engine '{name}'. Available: {available}"
    raise ValueError(msg)


def create_default_engine(**kwargs: Any) -> InferenceEngine:
    """Create the default engine (LiteLLM with Ollama backend).

    Respects AIOS_DEFAULT_MODEL env var. Falls back to ollama/llama3.2.
    """
    model = _TASK_MODELS["default"]
    return create_engine("litellm", model=model, **kwargs)


def auto_select_engine(task_type: str, **kwargs: Any) -> InferenceEngine:
    """Create the best engine for a given task type.

    task_type: "coding" | "vision" | "research" | "fast" | "reasoning" | "default"
    """
    model = _TASK_MODELS.get(task_type, _TASK_MODELS["default"])
    return create_engine("litellm", model=model, **kwargs)


def list_engines() -> list[str]:
    """List all registered engine names."""
    registered = [n for n in EngineRegistry.keys() if n not in _ENGINES]  # noqa: SIM118
    return sorted(set(list(_ENGINES.keys()) + registered))


def list_models() -> dict[str, str]:
    """Return a map of task_type → recommended model."""
    return dict(_TASK_MODELS)


__all__ = [
    "auto_select_engine",
    "create_default_engine",
    "create_engine",
    "list_engines",
    "list_models",
]
