"""AIOS Artifacts — versioned storage for agent/skill produced outputs.

An **artifact** is a named, immutable-versioned blob produced during a task
(e.g. a generated file, an image, a report). Storage is backend-agnostic: an
:class:`ArtifactStore` persists artifacts through an
:class:`ArtifactBackend` (memory or filesystem).
"""

from __future__ import annotations

import enum
import hashlib
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


class ArtifactKind(enum.StrEnum):
    """Typed artifact kinds produced by skills/agents.

    Each kind maps to a default content type used when none is supplied.
    """

    CODE = "code"
    MARKDOWN = "markdown"
    JSON = "json"
    REPORT = "report"
    PLAN = "plan"

    @property
    def content_type(self) -> str:
        return _KIND_CONTENT_TYPE[self]


_KIND_CONTENT_TYPE: dict[ArtifactKind, str] = {
    ArtifactKind.CODE: "text/x-code",
    ArtifactKind.MARKDOWN: "text/markdown",
    ArtifactKind.JSON: "application/json",
    ArtifactKind.REPORT: "text/plain",
    ArtifactKind.PLAN: "application/json",
}


@dataclass(frozen=True)
class Artifact:
    """A single versioned artifact.

    Attributes:
        id: Unique artifact id.
        name: Display name (may repeat across versions).
        version: Monotonic version integer (1-based).
        content: Raw bytes of the artifact.
        content_type: MIME-ish content type hint.
        kind: Optional typed kind (code/markdown/json/report/plan).
        metadata: Arbitrary metadata (e.g. producer skill, task id).
        created_at: Unix timestamp of creation.
        sha256: Content hash for integrity verification.
    """

    id: str
    name: str
    version: int
    content: bytes
    content_type: str = "application/octet-stream"
    kind: ArtifactKind | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    sha256: str = ""

    @property
    def size(self) -> int:
        """Byte size of the content."""
        return len(self.content)

    def verify(self) -> bool:
        """Verify the stored sha256 matches the content."""
        return self.sha256 == hashlib.sha256(self.content).hexdigest()


class ArtifactBackend(ABC):
    """Where artifacts are persisted."""

    @abstractmethod
    def save(self, artifact: Artifact) -> None:
        """Persist an artifact."""

    @abstractmethod
    def load(self, artifact_id: str) -> Artifact | None:
        """Load an artifact by id."""

    @abstractmethod
    def delete(self, artifact_id: str) -> bool:
        """Delete an artifact. Return True if removed."""

    @abstractmethod
    def ids(self) -> list[str]:
        """List all artifact ids."""


class MemoryArtifactBackend(ArtifactBackend):
    """In-memory artifact backend (testing, ephemeral runs)."""

    def __init__(self) -> None:
        self._store: dict[str, Artifact] = {}

    def save(self, artifact: Artifact) -> None:
        self._store[artifact.id] = artifact

    def load(self, artifact_id: str) -> Artifact | None:
        return self._store.get(artifact_id)

    def delete(self, artifact_id: str) -> bool:
        return self._store.pop(artifact_id, None) is not None

    def ids(self) -> list[str]:
        return list(self._store.keys())


class FilesystemArtifactBackend(ArtifactBackend):
    """Filesystem-backed artifact store.

    Each artifact is a directory ``<root>/<id>/v<version>`` containing the
    blob plus a sidecar ``.meta.json`` with metadata.
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).expanduser()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, artifact_id: str, version: int) -> Path:
        d = self._root / artifact_id
        return d / f"v{version}"

    def save(self, artifact: Artifact) -> None:
        import json

        blob_path = self._path(artifact.id, artifact.version)
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        blob_path.write_bytes(artifact.content)
        meta = {
            "id": artifact.id,
            "name": artifact.name,
            "version": artifact.version,
            "content_type": artifact.content_type,
            "kind": artifact.kind.value if artifact.kind is not None else None,
            "metadata": artifact.metadata,
            "created_at": artifact.created_at,
            "sha256": artifact.sha256,
        }
        (blob_path.parent / f"v{artifact.version}.meta.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )

    def load(self, artifact_id: str) -> Artifact | None:
        import json

        base = self._root / artifact_id
        if not base.is_dir():
            return None
        # Pick the highest version present.
        candidates = sorted(
            p.name for p in base.glob("v*.meta.json")
        )
        if not candidates:
            return None
        latest = candidates[-1]
        meta = json.loads((base / latest).read_text(encoding="utf-8"))
        version = int(latest[len("v"):-len(".meta.json")])
        blob = (base / f"v{version}").read_bytes()
        return Artifact(
            id=meta["id"],
            name=meta["name"],
            version=meta["version"],
            content=blob,
            content_type=meta["content_type"],
            kind=ArtifactKind(meta["kind"]) if meta.get("kind") else None,
            metadata=meta["metadata"],
            created_at=meta["created_at"],
            sha256=meta["sha256"],
        )

    def delete(self, artifact_id: str) -> bool:
        import shutil

        base = self._root / artifact_id
        if not base.is_dir():
            return False
        shutil.rmtree(base)
        return True

    def ids(self) -> list[str]:
        return [p.name for p in self._root.iterdir() if p.is_dir()]


@dataclass
class _VersionTracker:
    """Tracks latest version per artifact name for an in-memory store."""

    latest: dict[str, int] = field(default_factory=dict)

    def next(self, name: str) -> int:
        nxt = self.latest.get(name, 0) + 1
        self.latest[name] = nxt
        return nxt


class ArtifactStore:
    """High-level artifact store with versioning.

    Args:
        backend: Where artifacts are persisted (default: memory).
    """

    def __init__(self, backend: ArtifactBackend | None = None) -> None:
        self._backend = backend or MemoryArtifactBackend()
        self._versions = _VersionTracker()

    def put(
        self,
        name: str,
        content: bytes | str,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
        artifact_id: str | None = None,
        kind: ArtifactKind | None = None,
    ) -> Artifact:
        """Store a new artifact version. Returns the created artifact.

        If ``kind`` is supplied and ``content_type`` is omitted, the content
        type is derived from the kind's default mapping.
        """
        if isinstance(content, str):
            content = content.encode("utf-8")
        if content_type is None:
            content_type = kind.content_type if kind is not None else "application/octet-stream"
        aid = artifact_id or uuid.uuid4().hex
        version = self._versions.next(name)
        artifact = Artifact(
            id=aid,
            name=name,
            version=version,
            content=content,
            content_type=content_type,
            kind=kind,
            metadata=metadata or {},
            sha256=hashlib.sha256(content).hexdigest(),
        )
        self._backend.save(artifact)
        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        """Load an artifact by id."""
        return self._backend.load(artifact_id)

    def delete(self, artifact_id: str) -> bool:
        """Delete an artifact."""
        return self._backend.delete(artifact_id)

    def ids(self) -> list[str]:
        """List artifact ids."""
        return self._backend.ids()

    def list_artifacts(self) -> list[Artifact]:
        """Return all stored artifacts (latest version each id)."""
        return [a for a in (self.get(i) for i in self.ids()) if a is not None]


__all__ = [
    "Artifact",
    "ArtifactBackend",
    "ArtifactKind",
    "ArtifactStore",
    "FilesystemArtifactBackend",
    "MemoryArtifactBackend",
]
