"""AIOS-native desktop skills (Layer 2 of the AIOS core).

These skills implement capabilities with **AIOS-owned, offline-first** code.
They never require an external service. Optional providers (Composio, MCP,
GitHub API, Notion, Gmail, …) may later be registered for the same capability;
the :class:`~aios.platform.CapabilityResolver` prefers these native skills.

Skills here are kept intentionally small and real: they shell out to local
binaries (``git``, ``docker``) or use local filesystem / desktop APIs. Each
declares the catalog capability + frozen permission it requires so the platform
policy engine gates it correctly.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from aios.skills.base import Skill, SkillContext, SkillResult, SkillStatus
from aios.skills.manifest import SkillManifest

from .browser_skill import BROWSER_CAPABILITIES, BrowserConfigOpts, BrowserSkill

if TYPE_CHECKING:
    from aios.platform import CapabilityResolver
    from aios.skills.registry import SkillRegistry


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 60) -> tuple[int, str, str]:
    """Run a local command, returning (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(  # noqa: S603 - local, supervised commands only
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as exc:
        return 127, "", f"command not found: {exc}"
    except subprocess.TimeoutExpired as exc:
        return 124, "", f"timed out after {timeout}s: {exc}"


class TerminalSkill(Skill):
    """Run a shell command on the local machine."""

    def __init__(self) -> None:
        super().__init__(
            SkillManifest(
                name="terminal",
                version="1.0.0",
                description="Execute a shell command on the local machine",
                inputs=("command", "cwd", "timeout"),
                outputs=("stdout", "stderr", "returncode"),
                capabilities=("terminal.exec",),
                permissions=("PROCESS_EXEC",),
                approval="ask_once",
                tags=("desktop", "shell"),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        command = ctx.inputs.get("command")
        if not command:
            return SkillResult(status=SkillStatus.FAILED, error="missing 'command' input")
        cwd = ctx.inputs.get("cwd")
        timeout = int(ctx.inputs.get("timeout", 60))
        code, out, err = await asyncio.to_thread(
            _run, ["bash", "-c", command], cwd, timeout
        )
        return SkillResult(
            status=SkillStatus.SUCCESS if code == 0 else SkillStatus.FAILED,
            outputs={"stdout": out, "stderr": err, "returncode": code},
            steps=["spawn shell", f"exit={code}"],
            data={"command": command},
            error=err or None,
        )


class FilesystemSkill(Skill):
    """List / read / search files under a path (offline, local FS)."""

    def __init__(self) -> None:
        super().__init__(
            SkillManifest(
                name="filesystem",
                version="1.0.0",
                description="List, read, and search local files",
                inputs=("action", "path", "pattern"),
                outputs=("entries", "content"),
                capabilities=("filesystem.read",),
                permissions=("FILESYSTEM_READ",),
                approval="ask_once",
                tags=("desktop", "io"),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        action = ctx.inputs.get("action", "list")
        path = Path(ctx.inputs.get("path", ".")).expanduser()
        if action == "list":
            if not path.exists():
                return SkillResult(status=SkillStatus.FAILED, error=f"no such path: {path}")
            entries = [str(p) for p in sorted(path.iterdir())][:200]
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"entries": entries},
                steps=[f"listed {path}"],
            )
        if action == "read":
            if not path.is_file():
                return SkillResult(status=SkillStatus.FAILED, error=f"not a file: {path}")
            content = await asyncio.to_thread(path.read_text, errors="replace")
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"content": content},
                steps=[f"read {path}"],
            )
        if action == "search":
            pattern = ctx.inputs.get("pattern", "*")
            matches = [str(p) for p in sorted(path.rglob(pattern))][:200]
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"entries": matches},
                steps=[f"searched {pattern}"],
            )
        return SkillResult(status=SkillStatus.FAILED, error=f"unknown action: {action}")


class GitSkill(Skill):
    """Local git operations: status / log / diff (offline, no remote)."""

    def __init__(self) -> None:
        super().__init__(
            SkillManifest(
                name="git",
                version="1.0.0",
                description="Run local git commands (status, log, diff)",
                inputs=("subcommand", "repo"),
                outputs=("output", "returncode"),
                capabilities=("git.status",),
                permissions=("FILESYSTEM_READ", "PROCESS_EXEC"),
                approval="ask_once",
                tags=("desktop", "vcs"),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        sub = ctx.inputs.get("subcommand", "status")
        repo = ctx.inputs.get("repo", ".")
        cmd = ["git", "-C", repo, *sub.split()]
        code, out, err = await asyncio.to_thread(_run, cmd, repo, 60)
        return SkillResult(
            status=SkillStatus.SUCCESS if code == 0 else SkillStatus.FAILED,
            outputs={"output": out or err, "returncode": code},
            steps=[f"git {sub}"],
            error=err or None,
        )


class DockerSkill(Skill):
    """Local docker operations: ps / build / images (offline daemon)."""

    def __init__(self) -> None:
        super().__init__(
            SkillManifest(
                name="docker",
                version="1.0.0",
                description="Run local docker commands (ps, build, images)",
                inputs=("subcommand",),
                outputs=("output", "returncode"),
                capabilities=("docker.ps",),
                permissions=("PROCESS_EXEC",),
                approval="ask_once",
                tags=("desktop", "infra"),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        sub = ctx.inputs.get("subcommand", "ps")
        cmd = ["docker", *sub.split()]
        code, out, err = await asyncio.to_thread(_run, cmd, None, 120)
        return SkillResult(
            status=SkillStatus.SUCCESS if code == 0 else SkillStatus.FAILED,
            outputs={"output": out or err, "returncode": code},
            steps=[f"docker {sub}"],
            error=err or None,
        )


class NotesSkill(Skill):
    """Local markdown notebook — the native provider for ``notes.*``.

    Stores notes as markdown files under ``~/.aios/notes``. This is the
    offline-first implementation; Notion/Composio are optional providers that
    the resolver can prefer only if connected.
    """

    def __init__(self, notes_dir: str | None = None) -> None:
        self._notes_dir = Path(notes_dir or Path.home() / ".aios" / "notes")
        super().__init__(
            SkillManifest(
                name="notes",
                version="1.0.0",
                description="Create and read local markdown notes (offline notebook)",
                inputs=("action", "title", "body", "name"),
                outputs=("path", "content"),
                capabilities=("notes.write", "notes.read"),
                permissions=("FILESYSTEM_WRITE", "FILESYSTEM_READ"),
                approval="ask_once",
                tags=("desktop", "notes"),
            )
        )

    def _note_path(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return self._notes_dir / f"{safe}.md"

    async def run(self, ctx: SkillContext) -> SkillResult:
        action = ctx.inputs.get("action", "write")
        await asyncio.to_thread(self._notes_dir.mkdir, parents=True, exist_ok=True)
        if action == "write":
            title = ctx.inputs.get("title", "Untitled")
            body = ctx.inputs.get("body", "")
            name = ctx.inputs.get("name") or title
            path = self._note_path(name)
            content = f"# {title}\n\n{body}\n"
            await asyncio.to_thread(path.write_text, content)
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"path": str(path)},
                steps=[f"wrote {path}"],
            )
        if action == "read":
            name = ctx.inputs.get("name", "")
            path = self._note_path(name)
            if not path.exists():
                return SkillResult(status=SkillStatus.FAILED, error=f"no note: {name}")
            content = await asyncio.to_thread(path.read_text, errors="replace")
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"content": content},
                steps=[f"read {path}"],
            )
        return SkillResult(status=SkillStatus.FAILED, error=f"unknown action: {action}")


class NotifySkill(Skill):
    """Desktop notification via the native ``aios.desktop`` service."""

    def __init__(self) -> None:
        super().__init__(
            SkillManifest(
                name="notify",
                version="1.0.0",
                description="Show a desktop notification",
                inputs=("title", "message"),
                outputs=("sent",),
                capabilities=("desktop.notify",),
                permissions=("DESKTOP_NOTIFY",),
                approval="ask_once",
                tags=("desktop", "ux"),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        title = ctx.inputs.get("title", "AIOS")
        message = ctx.inputs.get("message", "")
        try:
            from aios.desktop.notifications import Notification, NotificationService

            svc = NotificationService()
            result = await svc.send(Notification(title=title, body=message))
            return SkillResult(
                status=SkillStatus.SUCCESS if result.ok else SkillStatus.FAILED,
                outputs={"sent": result.ok},
                steps=["shown notification"],
                error=None if result.ok else result.error,
            )
        except Exception as exc:
            return SkillResult(
                status=SkillStatus.FAILED, error=f"notify failed: {exc}"
            )


_NATIVE_SKILLS = (
    TerminalSkill,
    FilesystemSkill,
    GitSkill,
    DockerSkill,
    NotesSkill,
    NotifySkill,
    BrowserSkill,
)

# (skill name, capability(s) it provides natively)
_NATIVE_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "terminal": ("terminal.exec",),
    "filesystem": ("filesystem.read", "filesystem.write", "filesystem.search"),
    "git": ("git.status", "git.commit", "git.clone", "git.log"),
    "docker": ("docker.ps", "docker.build", "docker.images"),
    "notes": ("notes.write", "notes.read"),
    "notify": ("desktop.notify",),
    "browser": BROWSER_CAPABILITIES,
}


def register_native_skills(
    registry: SkillRegistry,
    resolver: CapabilityResolver | None = None,
) -> None:
    """Register all AIOS-native desktop skills and register them as the
    preferred (offline) providers in the capability resolver."""
    for skill_cls in _NATIVE_SKILLS:
        skill = skill_cls()
        registry.register(skill)
        if resolver is not None:
            for cap in _NATIVE_CAPABILITIES.get(skill.manifest.name, ()):
                resolver.register_native_skill(cap, skill.manifest.name)


__all__ = [
    "BROWSER_CAPABILITIES",
    "BrowserConfigOpts",
    "BrowserSkill",
    "DockerSkill",
    "FilesystemSkill",
    "GitSkill",
    "NotesSkill",
    "NotifySkill",
    "TerminalSkill",
    "register_native_skills",
]
