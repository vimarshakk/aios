"""M6 AutonomousPlanner — deterministic-first goal decomposition (ADR-0024).

Architecture (per the M6 design):

    Natural Language Goal
              │
              ▼
        Intent Classifier
         ┌────┴────┐
    Known goal  Unknown goal
         │          │
         ▼          ▼
     Template    LLM Planner (only if an LLM fn is configured)
         │          │
         └────┬─────┘
              ▼
        Canonical TaskGraph  (validated before execution)

Known, repeatable goals (e.g. "open Chrome", "commit my changes", "create a
note") route straight to a template — fast, offline, deterministic, testable.
Novel/ambiguous goals (e.g. "prepare me for tomorrow's meetings", "research
competitors and summarize them") fall through to the LLM planner when one is
available, emitting the same canonical schema. If no LLM is configured the
planner degrades gracefully to a best-effort single-step browser/notes plan or
a clear "cannot decompose" signal rather than fabricating capability ids.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .task_graph import Task, TaskGraph

# Capabilities that benefit from a bounded retry-with-backoff policy at plan
# time (network/IO prone). The runner honours each task's ``retry`` field.
_RETRY_CAPABILITY_PREFIXES = ("browser.", "git.", "docker.")

logger = logging.getLogger("aios.supervisor.planner")

# llm_fn: async callable(prompt) -> str
LLMFn = Callable[[str], Awaitable[str]]


@dataclass
class _TemplateResult:
    tasks: list[Task]
    confidence: float = 1.0


class _GoalTemplate:
    """A deterministic pattern → task-graph mapping."""

    def __init__(
        self,
        name: str,
        pattern: re.Pattern[str],
        build: Callable[[str, dict[str, Any]], list[Task]],
        confidence: float = 1.0,
    ) -> None:
        self.name = name
        self.pattern = pattern
        self.build = build
        self.confidence = confidence


def _browser_search_task(query: str, task_id: str = "browser") -> Task:
    return Task(
        id=task_id,
        capability="browser.search",
        action="search",
        inputs={"query": query},
        expected_output=f"search results for '{query}'",
    )


def _notes_write_task(title: str, body: str, depends: list[str], task_id: str = "notes") -> Task:
    return Task(
        id=task_id,
        capability="notes.write",
        action="write",
        inputs={"title": title, "body": body},
        depends_on=list(depends),
        expected_output=f"note saved: {title}",
    )


def _notify_task(message: str, depends: list[str], task_id: str = "notify") -> Task:
    return Task(
        id=task_id,
        capability="desktop.notify",
        action="notify",
        inputs={"title": "AIOS", "message": message},
        depends_on=list(depends),
        expected_output="desktop notification sent",
    )


def _build_summarize_pipeline(goal: str, query: str) -> list[Task]:
    """browser → (llm.summarize) → notes → notify."""
    browser = _browser_search_task(query)
    summarize = Task(
        id="summarize",
        capability="llm.summarize",
        action="summarize",
        inputs={"text_ref": "{{browser}}", "topic": query},
        depends_on=[browser.id],
        expected_output="concise summary text",
    )
    notes = _notes_write_task(
        title=f"Summary: {query}",
        body="{{summarize}}",
        depends=[summarize.id],
    )
    notify = _notify_task(f"Finished: {goal}", depends=[notes.id])
    return [browser, summarize, notes, notify]


# --- Template library (deterministic, offline) -----------------------------


def _tmpl_hackernews(goal: str, _caps: dict[str, Any]) -> list[Task]:
    return _build_summarize_pipeline(goal, "Hacker News top stories AI startup")


def _tmpl_summarize_query(goal: str, caps: dict[str, Any]) -> list[Task]:
    query = caps.get("query") or _extract_after(goal, ("summarize", "research", "about"))
    return _build_summarize_pipeline(goal, query or goal)


def _tmpl_create_note(goal: str, _caps: dict[str, Any]) -> list[Task]:
    title, body = _split_note(goal)
    return [
        _notes_write_task(title=title, body=body, depends=[]),
        _notify_task(f"Note saved: {title}", depends=["notes"]),
    ]


def _split_note(goal: str) -> tuple[str, str]:
    """Parse 'create a note called <Title> with body <Body>' into parts."""
    low = goal.lower()
    title: str | None = None
    body: str | None = None
    # Title: text after 'called'/'titled'/'named', up to 'with body' or end.
    for kw in ("called", "titled", "named"):
        idx = low.find(kw)
        if idx != -1:
            rest = goal[idx + len(kw):].strip()
            if "with body" in rest.lower():
                title, _, after = rest.partition("with body")
                title = title.strip(" .\":'")
                body = after.strip(" .\":'")
            else:
                title = rest.strip(" .\":'")
            break
    if title is None:
        title = "New note"
    if body is None:
        body = goal
    return title, body


def _tmpl_commit(goal: str, caps: dict[str, Any]) -> list[Task]:
    repo = caps.get("repo", ".")
    raw_msg = _extract_after(goal, ("commit", "with message", "message"))
    message = caps.get("message") or raw_msg or "chore: update"
    return [
        Task(
            id="git_status",
            capability="git.status",
            action="status",
            inputs={"repo": repo},
            expected_output="working tree status",
        ),
        Task(
            id="git_commit",
            capability="git.commit",
            action="commit",
            inputs={"repo": repo, "message": message},
            depends_on=["git_status"],
            expected_output="commit created",
        ),
        _notify_task(f"Committed: {message}", depends=["git_commit"]),
    ]


def _tmpl_git_read(goal: str, caps: dict[str, Any]) -> list[Task]:
    """Local git read operations (status / log / diff) — no network needed."""
    sub = "status"
    low = goal.lower()
    if "log" in low:
        sub = "log"
    elif "diff" in low:
        sub = "diff"
    repo = caps.get("repo", ".")
    return [
        Task(
            id="git_read",
            capability="git.status",
            action=sub,
            inputs={"repo": repo, "subcommand": sub},
            expected_output=f"git {sub} output",
        ),
        _notify_task(f"git {sub} complete", depends=["git_read"]),
    ]


def _tmpl_docker(goal: str, caps: dict[str, Any]) -> list[Task]:
    sub = caps.get("subcommand") or ("ps" if "container" in goal or "ps" in goal else "images")
    return [
        Task(
            id="docker",
            capability="docker.ps",
            action=sub if sub == "ps" else "images",
            inputs={"subcommand": sub},
            expected_output="docker output",
        ),
        _notify_task(f"Docker {sub} complete", depends=["docker"]),
    ]


def _tmpl_open(goal: str, caps: dict[str, Any]) -> list[Task]:
    url = caps.get("url") or _extract_url(goal) or "https://example.com"
    return [
        Task(
            id="browser",
            capability="browser.open",
            action="open",
            inputs={"url": url},
            expected_output=f"opened {url}",
        ),
        _notify_task(f"Opened {url}", depends=["browser"]),
    ]


def _tmpl_filesystem(goal: str, caps: dict[str, Any]) -> list[Task]:
    """Local filesystem intent — list/read/search, no network needed."""
    action = "search" if ("find" in goal or "search" in goal) else "list"
    if "read" in goal or "show" in goal or "contents" in goal:
        action = "read"
    raw = caps.get("path") or _extract_after(goal, ("in", "at", "under", "of")) or "."
    path = _resolve_fs_path(raw)
    return [
        Task(
            id="fs",
            capability="filesystem.read",
            action=action,
            inputs={"path": path},
            expected_output=f"filesystem {action} of {path}",
        ),
        _notify_task(f"Listed {path}", depends=["fs"]),
    ]


def _resolve_fs_path(raw: str) -> str:
    """Normalise a user-supplied path phrase to something the skill can stat.

    'home' / 'home directory' / 'the home directory' -> the user's HOME;
    otherwise keep the phrase (the skill will report a clear error if missing).
    """
    low = raw.strip().strip(" .\":'").lower()
    low = low.removeprefix("the ").removeprefix("my ").strip()
    if low in ("home", "home directory", "home folder", "home dir", "directory", "folder"):
        return str(Path.home())
    return raw.strip()


def _tmpl_terminal(goal: str, caps: dict[str, Any]) -> list[Task]:
    command = caps.get("command") or _extract_after(goal, ("run", "execute"))
    return [
        Task(
            id="term",
            capability="terminal.exec",
            action="run",
            inputs={"command": command or "echo done"},
            expected_output="command output",
        ),
        _notify_task("Command finished", depends=["term"]),
    ]


_TEMPLATES: list[_GoalTemplate] = [
    _GoalTemplate("hackernews", re.compile(r"hacker\s*news", re.IGNORECASE), _tmpl_hackernews),
    _GoalTemplate(
        "open",
        re.compile(
            r"\b(open|launch|visit|go to)\b.{0,15}\bhttps?://|https?://|"
            r"\b(open|launch|visit|go to)\b.{0,20}\b[a-z0-9-]+\.[a-z]{2,}\b",
            re.IGNORECASE,
        ),
        _tmpl_open,
    ),
    _GoalTemplate("commit", re.compile(r"\b(commit|git commit)\b", re.IGNORECASE), _tmpl_commit),
    _GoalTemplate(
        "git_read",
        re.compile(r"\b(git|show)\b.{0,20}\b(status|log|diff)\b", re.IGNORECASE),
        _tmpl_git_read,
    ),
    _GoalTemplate(
        "docker",
        re.compile(r"\b(docker|containers?)\b", re.IGNORECASE),
        _tmpl_docker,
    ),
    _GoalTemplate(
        "create_note",
        re.compile(
            r"\b(create|write|make|add|save|capture|jot|store|keep)\b.{0,30}\b(note|memo|notes)\b",
            re.IGNORECASE,
        ),
        _tmpl_create_note,
    ),
    _GoalTemplate(
        "filesystem",
        re.compile(
            r"\b(list|show|find|search|read|display)\b.{0,30}\b(files?|directory|folder|contents?|home)\b",
            re.IGNORECASE,
        ),
        _tmpl_filesystem,
    ),
    _GoalTemplate(
        "terminal",
        re.compile(r"\b(run|execute)\b.{0,20}(command|script|shell)", re.IGNORECASE),
        _tmpl_terminal,
    ),
    _GoalTemplate(
        "summarize",
        re.compile(r"\b(summar|research|find out about|learn about)\b", re.IGNORECASE),
        _tmpl_summarize_query,
    ),
]


# --- helpers -----------------------------------------------------------------


def _extract_after(text: str, keywords: tuple[str, ...]) -> str:
    low = text.lower()
    for kw in keywords:
        idx = low.find(kw)
        if idx != -1:
            return text[idx + len(kw) :].strip(" .\":'")
    return ""


def _extract_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s'\"]+", text)
    return m.group(0) if m else None


def _parse_llm_tasks(raw: str) -> list[Task]:
    """Parse an LLM response into canonical Tasks (best-effort)."""
    text = raw.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = data.get("tasks", [data])
    if not isinstance(data, list):
        return []
    tasks: list[Task] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cap = item.get("capability") or item.get("cap") or ""
        tasks.append(
            Task(
                id=item.get("id", uuid_fallback()),
                capability=str(cap),
                action=item.get("action", item.get("type", "")),
                inputs=item.get("inputs", {}) or {},
                depends_on=item.get("depends_on", []) or [],
                expected_output=item.get("expected_output", ""),
            )
        )
    return tasks


def uuid_fallback() -> str:
    import uuid

    return uuid.uuid4().hex[:12]


_LLM_PROMPT = """You are AIOS's planner. Decompose the user's goal into a task graph.

Goal: {goal}

Return ONLY a JSON object of the form:
{{
  "tasks": [
    {{
      "id": "unique_id",
      "capability": "logical.capability.id",
      "action": "verb",
      "inputs": {{"key": "value"}},
      "depends_on": ["other_id"],
      "expected_output": "short description"
    }}
  ]
}}

Use ONLY these capabilities when available:
- browser.open / browser.search / browser.screenshot / browser.extract_text
- notes.write / notes.read
- desktop.notify
- terminal.exec / filesystem.read / git.status / git.commit / docker.ps
- llm.summarize

"depends_on" must reference ids of earlier tasks. Max 12 tasks. No other text."""


class AutonomousPlanner:
    """Deterministic-first planner that emits a validated :class:`TaskGraph`.

    - Known goal shapes match a template and produce a typed DAG offline.
    - Unknown goals fall through to the LLM planner (if ``llm_fn`` configured),
      which emits the same canonical schema.
    - If nothing matches and no LLM is available, returns an empty graph so the
      caller can surface a clear "cannot decompose" outcome.
    """

    def __init__(self, llm_fn: LLMFn | None = None, max_llm_steps: int = 12) -> None:
        self.llm_fn = llm_fn
        self.max_llm_steps = max_llm_steps

    def plan(self, goal: str, capabilities: list[str] | None = None) -> TaskGraph:
        """Decompose ``goal`` into a canonical task graph (deterministic-first)."""
        caps = dict.fromkeys(capabilities or [], True)
        for template in _TEMPLATES:
            if template.pattern.search(goal):
                tasks = template.build(goal, caps)
                graph = TaskGraph(
                    goal=goal,
                    tasks=tasks,
                    metadata={"source": f"template:{template.name}"},
                )
                return self._apply_defaults(graph)
        return self._apply_defaults(self._plan_unknown(goal))

    async def plan_async(self, goal: str, capabilities: list[str] | None = None) -> TaskGraph:
        """Async variant; runs the LLM fallback when configured."""
        caps = dict.fromkeys(capabilities or [], True)
        for template in _TEMPLATES:
            if template.pattern.search(goal):
                tasks = template.build(goal, caps)
                graph = TaskGraph(
                    goal=goal,
                    tasks=tasks,
                    metadata={"source": f"template:{template.name}"},
                )
                return self._apply_defaults(graph)
        return self._apply_defaults(await self._plan_unknown_async(goal))

    @staticmethod
    def _apply_defaults(graph: TaskGraph) -> TaskGraph:
        """Inject retry policies + reflection flags for M6.1 robustness.

        Network-prone capabilities (browser/git/docker) get a bounded retry with
        backoff; every task keeps ``reflect=True`` so the runner's reflection
        hook can self-correct on failure.
        """
        for task in graph.tasks:
            if task.retry is None and any(
                task.capability.startswith(p) for p in _RETRY_CAPABILITY_PREFIXES
            ):
                task.retry = {"max_retries": 2, "backoff_seconds": 0.2}
        return graph

    def _plan_unknown(self, goal: str) -> TaskGraph:
        if self.llm_fn is None:
            tasks = _local_fallback(goal)
            return TaskGraph(goal=goal, tasks=tasks, metadata={"source": "fallback:local"})
        # Synchronous callers without an event loop cannot await the LLM; the
        # async path is preferred. Fall back to a local-first decomposition.
        tasks = _local_fallback(goal)
        return TaskGraph(goal=goal, tasks=tasks, metadata={"source": "fallback:sync-no-llm"})

    async def _plan_unknown_async(self, goal: str) -> TaskGraph:
        if self.llm_fn is None:
            tasks = _local_fallback(goal)
            return TaskGraph(goal=goal, tasks=tasks, metadata={"source": "fallback:local"})
        try:
            raw = await self.llm_fn(_LLM_PROMPT.format(goal=goal))
            tasks = _parse_llm_tasks(raw)[: self.max_llm_steps]
            if tasks:
                return TaskGraph(goal=goal, tasks=tasks, metadata={"source": "llm"})
        except Exception:
            logger.exception("LLM planning failed; using fallback decomposition")
        tasks = _local_fallback(goal)
        return TaskGraph(goal=goal, tasks=tasks, metadata={"source": "fallback:llm-error"})


def _local_fallback(goal: str) -> list[Task]:
    """Offline-first fallback for unrecognised goals.

    Prefers local capabilities (notes/notify) over a browser round-trip so the
    AI OS still completes meaningful work without network or a browser engine.
    Only the explicit ``hacker news`` / summarise / research / web-intent goals
    use the browser pipeline (which needs Playwright + network).
    """
    low = goal.lower()
    web_intent = any(
        w in low
        for w in ("hacker news", "summar", "research", "search the web", "find out about",
                  "learn about", "browse", "website", "web ", "http")
    )
    if web_intent:
        return _build_summarize_pipeline(goal, goal)
    # Local-only: capture the objective as a note and notify. When the phrase
    # looks like a note request, parse a title/body so the note is useful
    # rather than dumping the raw objective.
    if "note" in low or "memo" in low:
        title, body = _split_note(goal)
        return [
            _notes_write_task(title=title, body=body, depends=[]),
            _notify_task(f"Note saved: {title}", depends=["notes"]),
        ]
    return [
        _notes_write_task(title="Captured goal", body=goal, depends=[]),
        _notify_task(f"Captured: {goal[:60]}", depends=["notes"]),
    ]


__all__ = ["AutonomousPlanner", "LLMFn"]
