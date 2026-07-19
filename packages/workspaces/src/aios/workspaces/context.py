"""AIOS Workspaces — isolated execution contexts for agents.

A workspace binds together:

* a **root directory** (filesystem scope),
* a set of **assigned skills** (from the skills registry),
* a **scoped secret view** (prefix-based, reusing :mod:`aios.secrets`).

Workspaces are the unit of isolation for a running agent session. They compose
existing platform packages rather than reimplementing storage or skills.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.artifacts import ArtifactStore
    from aios.secrets import SecretStore
    from aios.skills.registry import SkillRegistry

from aios.workspaces.subsystems import (
    WorkspaceArtifacts,
    WorkspaceCache,
    WorkspaceHistory,
    WorkspaceMemory,
    WorkspacePermissions,
)


@dataclass
class WorkspaceConfig:
    """Configuration for a workspace.

    Attributes:
        id: Unique workspace identifier.
        name: Human-readable name.
        root: Filesystem root path for the workspace.
        skill_names: Skill names assigned to the workspace.
        secret_prefix: Prefix used to scope secrets for this workspace.
    """

    id: str
    name: str = ""
    root: str = "."
    skill_names: tuple[str, ...] = ()
    secret_prefix: str = "WS_"  # noqa: S105  (prefix, not a secret)


class Workspace:
    """An isolated execution context.

    Args:
        config: Workspace configuration.
        skills: A skill registry to resolve assigned skills from.
        secrets: An optional secret store for scoped secret access.
    """

    def __init__(
        self,
        config: WorkspaceConfig,
        skills: SkillRegistry | None = None,
        secrets: SecretStore | None = None,
        artifacts: ArtifactStore | None = None,
    ) -> None:
        self._config = config
        self._skills = skills
        self._secrets = secrets
        self._artifacts_store = artifacts
        self._root = Path(config.root).expanduser()
        self._memory = WorkspaceMemory()
        self._history = WorkspaceHistory()
        self._cache = WorkspaceCache()
        self._permissions = WorkspacePermissions()
        self._artifacts = (
            WorkspaceArtifacts(store=artifacts, workspace_id=config.id)
            if artifacts is not None
            else None
        )

    @property
    def id(self) -> str:
        """Workspace id."""
        return self._config.id

    @property
    def name(self) -> str:
        """Workspace name (falls back to id)."""
        return self._config.name or self._config.id

    @property
    def root(self) -> Path:
        """Workspace root path."""
        return self._root

    def ensure_root(self) -> Path:
        """Create the root directory if missing; return it."""
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root

    # -- sub-systems -------------------------------------------------------

    @property
    def memory(self) -> WorkspaceMemory:
        """Workspace-local scratch memory."""
        return self._memory

    @property
    def history(self) -> WorkspaceHistory:
        """Append-only action history."""
        return self._history

    @property
    def cache(self) -> WorkspaceCache:
        """In-memory cache with explicit invalidation."""
        return self._cache

    @property
    def permissions(self) -> WorkspacePermissions:
        """Scoped permission set for this workspace."""
        return self._permissions

    @permissions.setter
    def permissions(self, value: WorkspacePermissions) -> None:
        self._permissions = value

    @property
    def artifacts(self) -> WorkspaceArtifacts | None:
        """Typed artifact helper scoped to this workspace (if a store is set)."""
        return self._artifacts

    @property
    def assigned_skill_names(self) -> list[str]:
        """Names of skills assigned to this workspace."""
        return list(self._config.skill_names)

    def resolve_skills(self):
        """Resolve assigned skill names to skill instances.

        Returns a list of present skills; unregistered names are skipped.
        """
        if self._skills is None:
            return []
        return [
            s for name in self._config.skill_names
            if (s := self._skills.get(name)) is not None
        ]

    def has_skill(self, name: str) -> bool:
        """Whether the workspace has a given skill assigned AND registered."""
        if name not in self._config.skill_names:
            return False
        return self._skills is not None and self._skills.has(name)

    # -- secrets -----------------------------------------------------------

    def scoped_secret(self, key: str) -> str | None:
        """Read a secret scoped to this workspace (prefix + workspace id).

        The effective secret name is ``{secret_prefix}{WORKSPACE_ID}_{key}``.
        Returns None if no secret store or secret absent.
        """
        if self._secrets is None:
            return None
        scoped_name = f"{self._config.secret_prefix}{self._config.id.upper()}_{key}"
        if not self._secrets.exists(scoped_name):
            return None
        return self._secrets.get(scoped_name)

    def put_scoped_secret(self, key: str, value: str) -> None:
        """Store a secret scoped to this workspace."""
        if self._secrets is None:
            raise RuntimeError("Workspace has no secret store configured")
        scoped_name = f"{self._config.secret_prefix}{self._config.id.upper()}_{key}"
        self._secrets.put(scoped_name, value, accessed_by=f"workspace:{self.id}")


class WorkspaceManager:
    """In-memory registry of workspaces."""

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}

    def create(
        self,
        config: WorkspaceConfig,
        skills: SkillRegistry | None = None,
        secrets: SecretStore | None = None,
        artifacts: ArtifactStore | None = None,
    ) -> Workspace:
        """Create and register a workspace. Raises if id exists."""
        if config.id in self._workspaces:
            raise ValueError(f"Workspace '{config.id}' already exists")
        ws = Workspace(config, skills=skills, secrets=secrets, artifacts=artifacts)
        self._workspaces[config.id] = ws
        return ws

    def get(self, workspace_id: str) -> Workspace | None:
        """Get a workspace by id."""
        return self._workspaces.get(workspace_id)

    def remove(self, workspace_id: str) -> Workspace | None:
        """Remove a workspace by id."""
        return self._workspaces.pop(workspace_id, None)

    @property
    def ids(self) -> list[str]:
        """Registered workspace ids."""
        return list(self._workspaces.keys())

    def __contains__(self, workspace_id: str) -> bool:
        return workspace_id in self._workspaces

    def __len__(self) -> int:
        return len(self._workspaces)


__all__ = [
    "Workspace",
    "WorkspaceConfig",
    "WorkspaceManager",
]
