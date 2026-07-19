"""AIOS Workspaces package."""

from aios.workspaces.context import Workspace, WorkspaceConfig, WorkspaceManager
from aios.workspaces.subsystems import (
    HistoryEntry,
    WorkspaceArtifacts,
    WorkspaceCache,
    WorkspaceHistory,
    WorkspaceMemory,
    WorkspacePermissions,
)

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "HistoryEntry",
    "Workspace",
    "WorkspaceArtifacts",
    "WorkspaceCache",
    "WorkspaceConfig",
    "WorkspaceHistory",
    "WorkspaceManager",
    "WorkspaceMemory",
    "WorkspacePermissions",
]
