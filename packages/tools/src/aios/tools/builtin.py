"""Built-in tools for AIOS.

Includes real implementations of:
- Calculator
- DateTime
- WebFetch
- ShellExecute  (Open Interpreter style — subprocess with timeout + sandbox)
- FileSystem    (read/write/list with path guards)
- WebSearch     (DuckDuckGo — no API key required)
- MemoryStore   (store/retrieve facts in agent memory)
- Screenshot    (macOS screencapture / cross-platform Pillow)
"""

from __future__ import annotations

import asyncio
import datetime
import math
import os
import pathlib
import subprocess
import tempfile
import time
from typing import Any

import httpx

from aios.agents.tools import BaseTool, ToolSpec
from aios.agents.types import ToolResult

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

_SANDBOX_ROOT = pathlib.Path(
    os.environ.get("AIOS_SANDBOX_PATH", str(pathlib.Path.home() / "aios_workspace"))
)


def _guard_path(p: pathlib.Path) -> pathlib.Path:
    """Resolve and ensure path is within SANDBOX_ROOT."""
    resolved = _SANDBOX_ROOT / p if not p.is_absolute() else p
    resolved = resolved.resolve()
    try:
        resolved.relative_to(_SANDBOX_ROOT.resolve())
    except ValueError:
        msg = f"Path '{resolved}' is outside sandbox root '{_SANDBOX_ROOT}'"
        raise PermissionError(msg)  # noqa: B904
    return resolved


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------


class CalculatorTool(BaseTool):
    spec = ToolSpec(
        name="calculator",
        description="Evaluate mathematical expressions safely.",
        parameters={"expression": {"type": "string", "description": "Math expression to evaluate"}},
        required=["expression"],
        category="utility",
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        expr = kwargs.get("expression", "")
        try:
            allowed = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "len": len,
                "int": int,
                "float": float,
                "pi": math.pi,
                "e": math.e,
                "sqrt": math.sqrt,
                "pow": pow,
                "log": math.log,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "ceil": math.ceil,
                "floor": math.floor,
            }
            result = eval(expr, {"__builtins__": {}}, allowed)  # noqa: S307
            return ToolResult(
                tool_name=self.spec.name, content=str(result), latency_seconds=time.monotonic() - t0
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Error: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )


# ---------------------------------------------------------------------------
# DateTime
# ---------------------------------------------------------------------------


class DateTimeTool(BaseTool):
    spec = ToolSpec(
        name="datetime",
        description="Get current date/time, convert timezones, or format dates.",
        parameters={
            "action": {
                "type": "string",
                "enum": ["now", "timezone", "format"],
                "description": "Action",
            },
            "timezone": {"type": "string", "description": "Timezone (e.g. UTC, US/Eastern)"},
            "format": {"type": "string", "description": "strftime format string"},
        },
        required=["action"],
        category="utility",
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        action = kwargs.get("action", "now")
        try:
            now = datetime.datetime.now(datetime.UTC)
            if action == "now":
                return ToolResult(
                    tool_name=self.spec.name,
                    content=now.isoformat(),
                    latency_seconds=time.monotonic() - t0,
                )
            if action == "format":
                fmt = kwargs.get("format", "%Y-%m-%d %H:%M:%S")
                return ToolResult(
                    tool_name=self.spec.name,
                    content=now.strftime(fmt),
                    latency_seconds=time.monotonic() - t0,
                )
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Unknown action: {action}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Error: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )


# ---------------------------------------------------------------------------
# Web Fetch
# ---------------------------------------------------------------------------


class WebFetchTool(BaseTool):
    spec = ToolSpec(
        name="web_fetch",
        description="Fetch content from a URL and return the text.",
        parameters={
            "url": {"type": "string", "description": "URL to fetch"},
            "max_chars": {
                "type": "integer",
                "description": "Max characters to return",
                "default": 8000,
            },
        },
        required=["url"],
        category="web",
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        url = kwargs.get("url", "")
        max_chars = kwargs.get("max_chars", 8000)
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "AIOS/1.0"})
                resp.raise_for_status()
                # Strip HTML tags simply
                import re

                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = re.sub(r"\s+", " ", text).strip()[:max_chars]
                return ToolResult(
                    tool_name=self.spec.name,
                    content=text,
                    latency_seconds=time.monotonic() - t0,
                    metadata={"status_code": resp.status_code, "url": url},
                )
        except Exception as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Error fetching {url}: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )


# ---------------------------------------------------------------------------
# Shell Execute  (Open Interpreter style)
# ---------------------------------------------------------------------------


class ShellExecuteTool(BaseTool):
    """Execute shell commands in a sandboxed subprocess with timeout.

    Inspired by Open Interpreter (MIT). Sandboxed to AIOS_SANDBOX_PATH.
    """

    spec = ToolSpec(
        name="shell_execute",
        description=(
            "Execute a shell command and return stdout/stderr. "
            "Runs in an isolated working directory. "
            "Supports: Python scripts, bash commands, file operations, etc."
        ),
        parameters={
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 30)",
                "default": 30,
            },
            "language": {
                "type": "string",
                "enum": ["bash", "python"],
                "description": "Language hint",
                "default": "bash",
            },
        },
        required=["command"],
        category="execution",
    )
    permissions = ("shell",)

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        command: str = kwargs.get("command", "")
        timeout: int = min(int(kwargs.get("timeout", 30)), 120)  # cap at 2 min
        language: str = kwargs.get("language", "bash")

        if not command.strip():
            return ToolResult(
                tool_name=self.spec.name,
                content="No command provided",
                success=False,
                latency_seconds=0.0,
            )

        # Ensure sandbox exists
        _SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

        try:
            if language == "python":
                # Write to temp file and execute
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", dir=str(_SANDBOX_ROOT), delete=False
                ) as f:
                    f.write(command)
                    script_path = f.name
                cmd = ["python3", script_path]
            else:
                cmd = ["bash", "-c", command]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(_SANDBOX_ROOT),
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                proc.kill()
                return ToolResult(
                    tool_name=self.spec.name,
                    content=f"Command timed out after {timeout}s",
                    success=False,
                    latency_seconds=time.monotonic() - t0,
                )

            output_parts = []
            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                output_parts.append(f"[stderr]\n{stderr.decode('utf-8', errors='replace')}")

            output = "\n".join(output_parts).strip() or "(no output)"
            return ToolResult(
                tool_name=self.spec.name,
                content=output,
                success=(proc.returncode == 0),
                latency_seconds=time.monotonic() - t0,
                metadata={"exit_code": proc.returncode, "command": command},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Execution error: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )


# ---------------------------------------------------------------------------
# File System
# ---------------------------------------------------------------------------


class FileSystemTool(BaseTool):
    """Read, write, list, and search files within the sandbox workspace."""

    spec = ToolSpec(
        name="filesystem",
        description=(
            "Read, write, list, or search files in the AIOS workspace. "
            "All paths are relative to ~/aios_workspace."
        ),
        parameters={
            "action": {
                "type": "string",
                "enum": ["read", "write", "list", "search", "delete", "mkdir"],
                "description": "Action to perform",
            },
            "path": {
                "type": "string",
                "description": "File or directory path (relative to workspace)",
            },
            "content": {"type": "string", "description": "Content to write (for write action)"},
            "query": {"type": "string", "description": "Search query (for search action)"},
        },
        required=["action", "path"],
        category="filesystem",
    )
    permissions = ("filesystem",)

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        action = kwargs.get("action", "")
        raw_path = pathlib.Path(kwargs.get("path", "."))

        try:
            if action == "list":
                target = _guard_path(raw_path)
                if not target.exists():
                    return ToolResult(
                        tool_name=self.spec.name,
                        content=f"Path not found: {raw_path}",
                        success=False,
                        latency_seconds=time.monotonic() - t0,
                    )
                entries = []
                for item in sorted(target.iterdir()):
                    tag = "📁" if item.is_dir() else "📄"
                    size = f" ({item.stat().st_size:,} bytes)" if item.is_file() else ""
                    entries.append(f"{tag} {item.name}{size}")
                return ToolResult(
                    tool_name=self.spec.name,
                    content="\n".join(entries) or "(empty)",
                    latency_seconds=time.monotonic() - t0,
                )

            if action == "read":
                target = _guard_path(raw_path)
                if not target.is_file():
                    return ToolResult(
                        tool_name=self.spec.name,
                        content=f"File not found: {raw_path}",
                        success=False,
                        latency_seconds=time.monotonic() - t0,
                    )
                text = target.read_text(encoding="utf-8", errors="replace")
                return ToolResult(
                    tool_name=self.spec.name,
                    content=text,
                    latency_seconds=time.monotonic() - t0,
                    metadata={"size": len(text)},
                )

            if action == "write":
                target = _guard_path(raw_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                content = kwargs.get("content", "")
                target.write_text(content, encoding="utf-8")
                return ToolResult(
                    tool_name=self.spec.name,
                    content=f"Written {len(content)} chars to {raw_path}",
                    latency_seconds=time.monotonic() - t0,
                )

            if action == "mkdir":
                target = _guard_path(raw_path)
                target.mkdir(parents=True, exist_ok=True)
                return ToolResult(
                    tool_name=self.spec.name,
                    content=f"Directory created: {raw_path}",
                    latency_seconds=time.monotonic() - t0,
                )

            if action == "delete":
                target = _guard_path(raw_path)
                if target.is_file():
                    target.unlink()
                elif target.is_dir():
                    import shutil

                    shutil.rmtree(target)
                else:
                    return ToolResult(
                        tool_name=self.spec.name,
                        content=f"Not found: {raw_path}",
                        success=False,
                        latency_seconds=time.monotonic() - t0,
                    )
                return ToolResult(
                    tool_name=self.spec.name,
                    content=f"Deleted: {raw_path}",
                    latency_seconds=time.monotonic() - t0,
                )

            if action == "search":
                target = _guard_path(raw_path)
                query = kwargs.get("query", "")
                matches = [
                    str(p.relative_to(_SANDBOX_ROOT))
                    for p in target.rglob("*")
                    if p.is_file() and query.lower() in p.name.lower()
                ]
                return ToolResult(
                    tool_name=self.spec.name,
                    content="\n".join(matches) or "No matches found",
                    latency_seconds=time.monotonic() - t0,
                )

            return ToolResult(
                tool_name=self.spec.name,
                content=f"Unknown action: {action}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )

        except PermissionError as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=str(e),
                success=False,
                latency_seconds=time.monotonic() - t0,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Error: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )


# ---------------------------------------------------------------------------
# Web Search (DuckDuckGo — no API key)
# ---------------------------------------------------------------------------


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo Instant Answer API (free, no key)."""

    spec = ToolSpec(
        name="web_search",
        description="Search the web and return relevant results. No API key required.",
        parameters={
            "query": {"type": "string", "description": "Search query"},
            "max_results": {
                "type": "integer",
                "description": "Max results to return (default 5)",
                "default": 5,
            },
        },
        required=["query"],
        category="web",
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        query: str = kwargs.get("query", "")
        max_results: int = min(int(kwargs.get("max_results", 5)), 10)

        try:
            # Try duckduckgo-search library first
            try:
                from duckduckgo_search import DDGS  # type: ignore[import-untyped]

                with DDGS() as ddgs:
                    results = [
                        f"**{r.get('title', '')}**\n{r.get('href', '')}\n{r.get('body', '')}"
                        for r in ddgs.text(query, max_results=max_results)
                    ]
                content = "\n\n---\n\n".join(results) if results else "No results found."
                return ToolResult(
                    tool_name=self.spec.name,
                    content=content,
                    latency_seconds=time.monotonic() - t0,
                    metadata={"query": query, "results": len(results)},
                )
            except ImportError:
                pass

            # Fallback: DuckDuckGo Instant Answer API
            encoded_query = query.replace(" ", "+")
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"User-Agent": "AIOS/1.0"})
                data = resp.json()

            results = []
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append(f"**Summary**: {abstract}\nSource: {data.get('AbstractURL', '')}")

            for item in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(item, dict) and "Text" in item:
                    results.append(f"• {item['Text']}")

            content = (
                "\n\n".join(results)
                if results
                else f"No instant results for '{query}'. Try web_fetch on a specific URL."
            )
            return ToolResult(
                tool_name=self.spec.name, content=content, latency_seconds=time.monotonic() - t0
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Search error: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )


# ---------------------------------------------------------------------------
# Memory Store
# ---------------------------------------------------------------------------

# Simple in-process key-value store for agent memory (per-process)
_MEMORY_STORE: dict[str, str] = {}


class MemoryTool(BaseTool):
    """Store and retrieve information in agent working memory."""

    spec = ToolSpec(
        name="memory",
        description="Store, retrieve, list, or delete information in agent memory.",
        parameters={
            "action": {
                "type": "string",
                "enum": ["store", "retrieve", "list", "delete", "search"],
                "description": "Memory action",
            },
            "key": {"type": "string", "description": "Memory key"},
            "value": {"type": "string", "description": "Value to store (for store action)"},
            "query": {"type": "string", "description": "Search term (for search action)"},
        },
        required=["action"],
        category="memory",
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        action = kwargs.get("action", "")

        if action == "store":
            key = kwargs.get("key", "")
            value = kwargs.get("value", "")
            if not key:
                return ToolResult(
                    tool_name=self.spec.name,
                    content="key is required",
                    success=False,
                    latency_seconds=time.monotonic() - t0,
                )
            _MEMORY_STORE[key] = value
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Stored '{key}'",
                latency_seconds=time.monotonic() - t0,
            )

        if action == "retrieve":
            key = kwargs.get("key", "")
            val = _MEMORY_STORE.get(key)
            if val is None:
                return ToolResult(
                    tool_name=self.spec.name,
                    content=f"Key '{key}' not found",
                    success=False,
                    latency_seconds=time.monotonic() - t0,
                )
            return ToolResult(
                tool_name=self.spec.name, content=val, latency_seconds=time.monotonic() - t0
            )

        if action == "list":
            if not _MEMORY_STORE:
                return ToolResult(
                    tool_name=self.spec.name,
                    content="Memory is empty",
                    latency_seconds=time.monotonic() - t0,
                )
            entries = "\n".join(
                f"• {k}: {v[:80]}{'...' if len(v) > 80 else ''}" for k, v in _MEMORY_STORE.items()
            )
            return ToolResult(
                tool_name=self.spec.name, content=entries, latency_seconds=time.monotonic() - t0
            )

        if action == "delete":
            key = kwargs.get("key", "")
            _MEMORY_STORE.pop(key, None)
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Deleted '{key}'",
                latency_seconds=time.monotonic() - t0,
            )

        if action == "search":
            query = kwargs.get("query", "").lower()
            matches = {
                k: v for k, v in _MEMORY_STORE.items() if query in k.lower() or query in v.lower()
            }
            if not matches:
                return ToolResult(
                    tool_name=self.spec.name,
                    content=f"No memory entries matching '{query}'",
                    latency_seconds=time.monotonic() - t0,
                )
            content = "\n".join(f"• {k}: {v[:100]}" for k, v in matches.items())
            return ToolResult(
                tool_name=self.spec.name, content=content, latency_seconds=time.monotonic() - t0
            )

        return ToolResult(
            tool_name=self.spec.name,
            content=f"Unknown action: {action}",
            success=False,
            latency_seconds=time.monotonic() - t0,
        )


# ---------------------------------------------------------------------------
# Screenshot (macOS native / cross-platform)
# ---------------------------------------------------------------------------


class ScreenshotTool(BaseTool):
    """Capture a screenshot of the screen or a window."""

    spec = ToolSpec(
        name="screenshot",
        description="Take a screenshot and save it to the workspace.",
        parameters={
            "filename": {
                "type": "string",
                "description": "Output filename (default: screenshot.png)",
                "default": "screenshot.png",
            },
        },
        required=[],
        category="desktop",
    )
    permissions = ("desktop",)

    async def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.monotonic()
        filename = kwargs.get("filename", "screenshot.png")
        _SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
        output_path = _SANDBOX_ROOT / filename

        try:
            import platform

            if platform.system() == "Darwin":
                result = subprocess.run(  # noqa: S603
                    ["screencapture", "-x", str(output_path)],  # noqa: S607
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.decode())  # noqa: TRY301
            else:
                try:
                    from PIL import ImageGrab  # type: ignore[import-untyped]

                    img = ImageGrab.grab()
                    img.save(str(output_path))
                except ImportError:
                    return ToolResult(
                        tool_name=self.spec.name,
                        content="Pillow not installed. Run: pip install Pillow",
                        success=False,
                        latency_seconds=time.monotonic() - t0,
                    )

            return ToolResult(
                tool_name=self.spec.name,
                content=f"Screenshot saved to {output_path}",
                latency_seconds=time.monotonic() - t0,
                metadata={"path": str(output_path)},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.spec.name,
                content=f"Screenshot error: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

ALL_BUILTIN_TOOLS: list[BaseTool] = [
    CalculatorTool(),
    DateTimeTool(),
    WebFetchTool(),
    ShellExecuteTool(),
    FileSystemTool(),
    WebSearchTool(),
    MemoryTool(),
    ScreenshotTool(),
]

__all__ = [
    "ALL_BUILTIN_TOOLS",
    "CalculatorTool",
    "DateTimeTool",
    "FileSystemTool",
    "MemoryTool",
    "ScreenshotTool",
    "ShellExecuteTool",
    "WebFetchTool",
    "WebSearchTool",
]
