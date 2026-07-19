"""Tests for aios.artifacts — versioned artifact storage."""

from __future__ import annotations

from aios.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactStore,
    FilesystemArtifactBackend,
    MemoryArtifactBackend,
)


class TestArtifact:
    def test_sha_and_verify(self) -> None:
        a = Artifact(
            id="x", name="f", version=1, content=b"hello",
            sha256="2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )
        assert a.size == 5
        assert a.verify()

    def test_verify_fails_on_tamper(self) -> None:
        a = Artifact(id="x", name="f", version=1, content=b"hello", sha256="deadbeef")
        assert not a.verify()


class TestMemoryStore:
    def test_put_get_versions(self) -> None:
        store = ArtifactStore(MemoryArtifactBackend())
        a1 = store.put("report", b"v1")
        a2 = store.put("report", b"v2", artifact_id=a1.id)
        assert a1.version == 1
        assert a2.version == 2
        assert store.get(a1.id) is a2  # latest version returned
        assert len(store.ids()) == 1
        assert store.list_artifacts()[0].content == b"v2"

    def test_delete(self) -> None:
        store = ArtifactStore(MemoryArtifactBackend())
        a = store.put("f", b"x")
        assert store.delete(a.id)
        assert store.get(a.id) is None
        assert not store.delete(a.id)


class TestFilesystemStore:
    def test_roundtrip(self, tmp_path) -> None:
        backend = FilesystemArtifactBackend(tmp_path / "arts")
        store = ArtifactStore(backend)
        a = store.put("img", b"binary-data", content_type="image/png",
                      metadata={"producer": "skill-a"})
        loaded = store.get(a.id)
        assert loaded is not None
        assert loaded.content == b"binary-data"
        assert loaded.content_type == "image/png"
        assert loaded.metadata["producer"] == "skill-a"
        assert loaded.verify()

    def test_fs_delete(self, tmp_path) -> None:
        backend = FilesystemArtifactBackend(tmp_path / "arts2")
        store = ArtifactStore(backend)
        a = store.put("x", b"1")
        assert store.delete(a.id)
        assert store.get(a.id) is None


class TestArtifactKind:
    def test_content_type_derived_from_kind(self) -> None:
        assert ArtifactKind.MARKDOWN.content_type == "text/markdown"
        assert ArtifactKind.JSON.content_type == "application/json"

    def test_put_with_kind_derives_content_type(self) -> None:
        store = ArtifactStore(MemoryArtifactBackend())
        a = store.put("readme", "# Title", kind=ArtifactKind.MARKDOWN)
        assert a.kind == ArtifactKind.MARKDOWN
        assert a.content_type == "text/markdown"
        assert a.content == b"# Title"

    def test_put_explicit_content_type_wins(self) -> None:
        store = ArtifactStore(MemoryArtifactBackend())
        a = store.put(
            "data", b"{}", kind=ArtifactKind.JSON, content_type="application/custom+json"
        )
        assert a.content_type == "application/custom+json"

    def test_fs_artifact_persists_kind(self, tmp_path) -> None:
        backend = FilesystemArtifactBackend(tmp_path / "arts3")
        store = ArtifactStore(backend)
        a = store.put("plan", '{"steps":[]}', kind=ArtifactKind.PLAN)
        loaded = store.get(a.id)
        assert loaded is not None
        assert loaded.kind == ArtifactKind.PLAN
