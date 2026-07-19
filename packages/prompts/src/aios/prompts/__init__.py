"""AIOS Prompts package."""

from aios.prompts.templates import (
    PromptLibrary,
    PromptPart,
    PromptRole,
    PromptTemplate,
    PromptVersion,
    coder_prompt,
    default_library,
    planner_prompt,
    research_prompt,
    reviewer_prompt,
    system_prompt,
)

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "PromptLibrary",
    "PromptPart",
    "PromptRole",
    "PromptTemplate",
    "PromptVersion",
    "coder_prompt",
    "default_library",
    "planner_prompt",
    "research_prompt",
    "reviewer_prompt",
    "system_prompt",
]
