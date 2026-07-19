"""Tests for aios.secrets — encrypted secret storage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aios.secrets import (
    EnvBackend,
    KeychainBackend,
    MemoryBackend,
    RemoteVaultBackend,
    SecretError,
    SecretRecord,
    SecretStore,
)
from aios.security.encryption import VaultEncryptor


@pytest.fixture
def encryptor() -> VaultEncryptor:
    return VaultEncryptor.from_password("test-master-key")


class TestMemoryBackend:
    def test_store_fetch_delete(self) -> None:
        b = MemoryBackend()
        b.store(SecretRecord(name="k", ciphertext="ct"))
        assert b.fetch("k") is not None
        assert b.delete("k") is True
        assert b.fetch("k") is None
        assert b.names() == []


class TestEnvBackend:
    def test_roundtrip(self) -> None:
        b = EnvBackend(prefix="AIOS_TEST_SECRET_")
        b.store(SecretRecord(name="api", ciphertext="enc"))
        assert b.fetch("api") is not None
        assert "api" in b.names()
        b.delete("api")
        assert b.fetch("api") is None


class TestSecretStore:
    def test_put_and_get(self, encryptor: VaultEncryptor) -> None:
        store = SecretStore(encryptor)
        store.put("db_password", "s3cr3t")
        assert store.get("db_password") == "s3cr3t"
        assert store.exists("db_password")

    def test_get_missing_raises(self, encryptor: VaultEncryptor) -> None:
        store = SecretStore(encryptor)
        with pytest.raises(SecretError, match="not found"):
            store.get("nope")

    def test_values_never_stored_plaintext(self, encryptor: VaultEncryptor) -> None:
        store = SecretStore(encryptor, backend=MemoryBackend())
        store.put("k", "plaintext-value")
        rec = store._backend.fetch("k")
        assert rec is not None
        assert "plaintext-value" not in rec.ciphertext

    def test_delete(self, encryptor: VaultEncryptor) -> None:
        store = SecretStore(encryptor)
        store.put("k", "v")
        assert store.delete("k") is True
        assert not store.exists("k")

    def test_access_log(self, encryptor: VaultEncryptor) -> None:
        store = SecretStore(encryptor)
        store.put("k", "v")
        store.get("k")
        with pytest.raises(SecretError):
            store.get("missing")
        log = store.access_log()
        assert any(e.name == "k" and e.ok for e in log)
        assert any(e.name == "missing" and not e.ok for e in log)

    def test_list_names_excludes_values(self, encryptor: VaultEncryptor) -> None:
        store = SecretStore(encryptor)
        store.put("a", "1")
        store.put("b", "2")
        assert set(store.list_names()) == {"a", "b"}

    def test_env_backend_integration(self, encryptor: VaultEncryptor) -> None:
        store = SecretStore(encryptor, backend=EnvBackend(prefix="AIOS_T2_"))
        store.put("token", "xyz")
        assert store.get("token") == "xyz"
        store.delete("token")
        assert not store.exists("token")


class TestKeychainBackend:
    def test_fallback_when_keyring_missing(self) -> None:
        b = KeychainBackend(service_name="aios-test")
        # No keyring installed in test env -> fallback path.
        b.store(SecretRecord(name="k", ciphertext="ct"))
        rec = b.fetch("k")
        assert rec is not None
        assert rec.ciphertext == "ct"
        assert "k" in b.names()
        assert b.delete("k") is True
        assert b.fetch("k") is None


class TestRemoteVaultBackend:
    def _fake_urlopen(self, stored: dict[str, bytes]):
        def _open(req, timeout=0.0):
            resp = MagicMock()
            # `with urlopen(...) as resp` invokes resp.__enter__() -> resp
            resp.__enter__.return_value = resp
            if req.method == "PUT":
                stored[req.full_url.split("/")[-1]] = req.data
                resp.read.return_value = b"ok"
            else:
                resp.read.return_value = stored.get(
                    req.full_url.split("/")[-1], b""
                )
            return resp

        return _open

    def test_store_and_fetch(self) -> None:
        b = RemoteVaultBackend(base_url="http://vault.local", token="t")  # noqa: S106
        stored: dict[str, bytes] = {}
        with patch("urllib.request.urlopen", side_effect=self._fake_urlopen(stored)):
            b.store(SecretRecord(name="k", ciphertext="ciphertext-blob"))
            rec = b.fetch("k")
        assert rec is not None
        assert rec.ciphertext == "ciphertext-blob"
        assert rec.backend == "vault"

    def test_fetch_404_returns_none(self) -> None:
        import urllib.error

        b = RemoteVaultBackend(base_url="http://vault.local")
        http_err = urllib.error.HTTPError(
            url="x", code=404, msg="nf", hdrs=None, fp=None
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            assert b.fetch("missing") is None

    def test_store_failure_raises(self) -> None:
        import urllib.error

        b = RemoteVaultBackend(base_url="http://vault.local")
        http_err = urllib.error.HTTPError(
            url="x", code=500, msg="boom", hdrs=None, fp=None
        )
        with patch("urllib.request.urlopen", side_effect=http_err), pytest.raises(
            SecretError
        ):
            b.store(SecretRecord(name="k", ciphertext="ct"))

    def test_store_via_secret_store(self, encryptor: VaultEncryptor) -> None:
        b = RemoteVaultBackend(base_url="http://vault.local")
        stored: dict[str, bytes] = {}
        with patch("urllib.request.urlopen", side_effect=self._fake_urlopen(stored)):
            store = SecretStore(encryptor, backend=b)
            store.put("v", "value")
            assert store.get("v") == "value"
