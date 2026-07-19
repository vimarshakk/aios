"""AIOS Prompts — composable, reusable prompt templates.

A :class:`PromptTemplate` is a named, variable-driven prompt rendered from
parts. :class:`PromptPart` lets you compose prompts from reusable sections,
and :class:`PromptLibrary` registers and resolves named prompts.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence


_VARIABLE_RE = re.compile(r"\{\{?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}?\}")


@dataclass
class PromptPart:
    """A reusable, composable section of a prompt.

    Args:
        name: Unique part name (also the render key when included).
        body: Template text. May contain ``{{var}}`` placeholders.
        required: Variable names that must be supplied when rendering.
    """

    name: str
    body: str
    required: tuple[str, ...] = ()

    def variables(self) -> set[str]:
        """Return the set of variable names referenced in the body."""
        return {m.group(1) for m in _VARIABLE_RE.finditer(self.body)}


@dataclass
class PromptTemplate:
    """A named prompt composed of ordered parts.

    Args:
        name: Unique template name.
        parts: Ordered parts to render in sequence.
        variables: Declared input variable names (for validation).
        description: Optional human description.
    """

    name: str
    parts: tuple[PromptPart, ...]
    variables: tuple[str, ...] = ()
    description: str = ""

    def render(self, **values: object) -> str:
        """Render the prompt, substituting ``values`` for variables."""
        missing = set(self.variables) - set(values.keys())
        if missing:
            raise KeyError(f"Missing prompt variables: {sorted(missing)}")
        out = [_render_part(part, values) for part in self.parts]
        return "\n\n".join(out).strip()

    def render_map(self, values: Mapping[str, object]) -> str:
        """Render from a mapping instead of kwargs."""
        return self.render(**dict(values))


class PromptRole(enum.StrEnum):
    """Canonical prompt roles used across the developer platform."""

    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    RESEARCH = "research"
    SYSTEM = "system"


@dataclass(frozen=True)
class PromptVersion:
    """An immutable version stamp for a prompt template.

    Attributes:
        version: Semantic-ish version string (e.g. ``"1.0.0"``).
        changelog: Optional note describing what changed in this version.
    """

    version: str
    changelog: str = ""

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PromptVersion):
            return NotImplemented
        return _semver_key(self.version) < _semver_key(other.version)


def _semver_key(v: str) -> tuple[int, ...]:
    parts = re.split(r"[.\-+]", v)
    out: list[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            break
    return tuple(out)


def _render_part(part: PromptPart, values: Mapping[str, object]) -> str:
    try:
        return part.body.format(**values)
    except (KeyError, IndexError):
        # Tolerate single-brace Jinja-style placeholders by substituting
        # any unmatched variables with an empty string.
        def _sub(m: re.Match[str]) -> str:
            key = m.group(1)
            val = values.get(key)
            return str(val) if val is not None else ""

        return _VARIABLE_RE.sub(_sub, part.body)


class PromptLibrary:
    """Registry of named :class:`PromptTemplate` and :class:`PromptPart`."""

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._parts: dict[str, PromptPart] = {}

    def register_part(self, part: PromptPart) -> None:
        self._parts[part.name] = part

    def register_template(self, template: PromptTemplate) -> None:
        self._templates[template.name] = template

    def get_template(self, name: str) -> PromptTemplate | None:
        return self._templates.get(name)

    def get_part(self, name: str) -> PromptPart | None:
        return self._parts.get(name)

    def build(
        self,
        name: str,
        parts: Sequence[str | PromptPart],
        variables: Iterable[str] = (),
        description: str = "",
    ) -> PromptTemplate:
        """Build and register a template from part names/objects."""
        resolved: list[PromptPart] = []
        for p in parts:
            if isinstance(p, PromptPart):
                resolved.append(p)
            else:
                part = self._parts.get(p)
                if part is None:
                    raise KeyError(f"Unknown prompt part: {p}")
                resolved.append(part)
        template = PromptTemplate(
            name=name,
            parts=tuple(resolved),
            variables=tuple(variables),
            description=description,
        )
        self.register_template(template)
        return template

    def render(self, name: str, **values: object) -> str:
        """Render a registered template by name."""
        tpl = self.get_template(name)
        if tpl is None:
            raise KeyError(f"Unknown prompt template: {name}")
        return tpl.render(**values)

    @property
    def template_names(self) -> list[str]:
        return list(self._templates.keys())


def _builtin_parts() -> list[PromptPart]:
    return [
        PromptPart(
            name="role",
            body="You are {role}.",
            required=("role",),
        ),
        PromptPart(
            name="objective",
            body="Objective: {objective}",
            required=("objective",),
        ),
        PromptPart(
            name="context_block",
            body="Context:\n{context}",
            required=("context",),
        ),
        PromptPart(
            name="constraints",
            body="Constraints:\n- {constraints}",
            required=("constraints",),
        ),
        PromptPart(
            name="output_format",
            body="Respond in the following format:\n{format}",
            required=("format",),
        ),
    ]


def _role_template(
    role: PromptRole,
    body: str,
    variables: list[str],
    description: str,
) -> PromptTemplate:
    """Build a role-scoped template from a role declaration + body part."""
    return PromptTemplate(
        name=f"role_{role.value}",
        parts=(
            PromptPart(name=f"role_{role.value}", body=f"You are a {role.value}.", required=()),
            PromptPart(name=f"body_{role.value}", body=body, required=tuple(variables)),
        ),
        variables=tuple(variables),
        description=description,
    )


def planner_prompt() -> PromptTemplate:
    """Planner role: decompose a goal into an ordered, dependency-aware plan."""
    return _role_template(
        PromptRole.PLANNER,
        "Goal: {goal}\n\nBreak it into ordered steps. Each step has an id, "
        "description, and dependencies. Output JSON with keys "
        "steps, risks, and assumptions.",
        ["goal"],
        "Decompose a goal into a structured plan.",
    )


def coder_prompt() -> PromptTemplate:
    """Coder role: implement a single step to a clean, tested result."""
    return _role_template(
        PromptRole.CODER,
        "Task: {task}\nContext:\n{context}\n\nWrite code that satisfies the "
        "task. Prefer minimal, readable implementations and include tests.",
        ["task", "context"],
        "Implement a single task with code.",
    )


def reviewer_prompt() -> PromptTemplate:
    """Reviewer role: critique code for correctness, security, and style."""
    return _role_template(
        PromptRole.REVIEWER,
        "Review the following diff for bugs, security, and style:\n"
        "```\n{diff}\n```\n\nReturn a list of findings with severity and "
        "suggested fix.",
        ["diff"],
        "Review a code diff.",
    )


def research_prompt() -> PromptTemplate:
    """Research role: gather and synthesize findings on a question."""
    return _role_template(
        PromptRole.RESEARCH,
        "Question: {question}\nKnown sources:\n{sources}\n\nProduce a concise "
        "synthesis with citations and open unknowns.",
        ["question", "sources"],
        "Research and synthesize a question.",
    )


def system_prompt() -> PromptTemplate:
    """System role: top-level behavioral guardrails for an agent."""
    return _role_template(
        PromptRole.SYSTEM,
        "You are {agent_name}, operating under these rules:\n{rules}\n"
        "Always explain decisions and refuse unsafe actions.",
        ["agent_name", "rules"],
        "Top-level system guardrails for an agent.",
    )


def default_library() -> PromptLibrary:
    """Create a :class:`PromptLibrary` seeded with builtin parts/templates."""
    lib = PromptLibrary()
    for part in _builtin_parts():
        lib.register_part(part)
    lib.build(
        "agent_task",
        ["role", "objective", "context_block", "constraints", "output_format"],
        variables=["role", "objective", "context", "constraints", "format"],
        description="General agent task prompt.",
    )
    lib.build(
        "code_review",
        [
            PromptPart(
                name="role_cr",
                body="You are a senior {language} code reviewer.",
                required=("language",),
            ),
            PromptPart(
                name="objective_cr",
                body="Review the following code for bugs, security, and style:",
            ),
            PromptPart(
                name="context_block",
                body="Code:\n```\n{code}\n```",
                required=("code",),
            ),
        ],
        variables=["language", "code"],
        description="Code review prompt.",
    )
    for builder in (
        planner_prompt,
        coder_prompt,
        reviewer_prompt,
        research_prompt,
        system_prompt,
    ):
        lib.register_template(builder())
    return lib


__all__ = [
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
