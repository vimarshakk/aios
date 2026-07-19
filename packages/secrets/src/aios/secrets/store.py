"""AIOS Secrets — encrypted, backend-agnostic secret storage.

Secrets are stored encrypted at rest using the existing
:class:`aios.security.encryption.VaultEncryptor` (no new crypto abstraction).
A *backend* decides where ciphertext lives (memory, env vars, future: vault);
the store is responsible for encrypt/decrypt and access logging.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.security.encryption import VaultEncryptor


class SecretError(Exception):
    """Raised when a secret operation fails (e.g. missing key)."""


@dataclass
class SecretRecord:
    """An encrypted secret record."""

    name: str
    ciphertext: str
    backend: str = "memory"

    @property
    def is_encrypted(self) -> bool:
        return bool(self.ciphertext)


class SecretBackend(ABC):
    """Where encrypted secrets live. Implementations persist ciphertext."""

    @abstractmethod
    def store(self, record: SecretRecord) -> None:
        """Persist a secret record."""

    @abstractmethod
    def fetch(self, name: str) -> SecretRecord | None:
        """Retrieve a secret record by name, or None."""

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete a secret by name. Return True if removed."""

    @abstractmethod
    def names(self) -> list[str]:
        """List stored secret names."""


class MemoryBackend(SecretBackend):
    """In-memory backend (testing, single-process)."""

    def __init__(self) -> None:
        self._store: dict[str, SecretRecord] = {}

    def store(self, record: SecretRecord) -> None:
        self._store[record.name] = record

    def fetch(self, name: str) -> SecretRecord | None:
        return self._store.get(name)

    def delete(self, name: str) -> bool:
        return self._store.pop(name, None) is not None

    def names(self) -> list[str]:
        return list(self._store.keys())


class EnvBackend(SecretBackend):
    """Backend that mirrors secrets into process environment variables.

    Ciphertext is stored in the environment under ``AIOS_SECRET_<NAME>``.
    """

    def __init__(self, prefix: str = "AIOS_SECRET_") -> None:
        self._prefix = prefix

    def _key(self, name: str) -> str:
        return f"{self._prefix}{name.upper()}"

    def store(self, record: SecretRecord) -> None:
        os.environ[self._key(record.name)] = record.ciphertext

    def fetch(self, name: str) -> SecretRecord | None:
        raw = os.environ.get(self._key(name))
        if raw is None:
            return None
        return SecretRecord(name=name, ciphertext=raw, backend="env")

    def delete(self, name: str) -> bool:
        return os.environ.pop(self._key(name), None) is not None

    def names(self) -> list[str]:
        return [
            k[len(self._prefix):].lower()
            for k in os.environ
            if k.startswith(self._prefix)
        ]


class KeychainBackend(SecretBackend):
    """Backend that stores ciphertext in the OS keychain via ``keyring``.

    Falls back to an in-memory store if ``keyring`` is not installed, so the
    backend remains usable in headless/test environments.
    """

    def __init__(self, service_name: str = "aios") -> None:
        self._service = service_name
        self._fallback: dict[str, SecretRecord] = {}
        try:
            import keyring  # type: ignore[import-untyped]

            self._keyring = keyring
        except ImportError:
            self._keyring = None  # type: ignore[assignment]

    def _set(self, record: SecretRecord) -> None:
        if self._keyring is None:
            self._fallback[record.name] = record
            return
        self._keyring.set_password(self._service, record.name, record.ciphertext)

    def _get_raw(self, name: str) -> str | None:
        if self._keyring is None:
            rec = self._fallback.get(name)
            return rec.ciphertext if rec is not None else None
        try:
            return self._keyring.get_password(self._service, name)  # type: ignore[union-attr]
        except Exception:
            return None

    def store(self, record: SecretRecord) -> None:
        self._set(record)

    def fetch(self, name: str) -> SecretRecord | None:
        raw = self._get_raw(name)
        if raw is None:
            return None
        return SecretRecord(name=name, ciphertext=raw, backend="keychain")

    def delete(self, name: str) -> bool:
        if self._keyring is None:
            return self._fallback.pop(name, None) is not None
        try:
            self._keyring.delete_password(self._service, name)  # type: ignore[union-attr]
        except Exception:
            return False
        return True

    def names(self) -> list[str]:
        if self._keyring is None:
            return list(self._fallback.keys())
        # The keyring API has no portable list; enumerate via get_credential
        # is unsupported, so report the in-memory mirror only.
        return list(self._fallback.keys())


class RemoteVaultBackend(SecretBackend):
    """Backend that stores ciphertext in a remote vault over HTTP.

    The remote service is expected to expose ``PUT/GET/DELETE`` on
    ``{base_url}/secrets/{name}`` returning the ciphertext as the body.
    Failures raise :class:`SecretError` so callers can decide on retry policy.
    """

    def __init__(self, base_url: str, token: str = "", timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "text/plain"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _url(self, name: str) -> str:
        return f"{self._base}/secrets/{name}"

    def store(self, record: SecretRecord) -> None:
        req = urllib.request.Request(
            self._url(record.name),
            data=record.ciphertext.encode("utf-8"),
            headers=self._headers(),
            method="PUT",
        )
        try:
            urllib.request.urlopen(req, timeout=self._timeout)
        except urllib.error.URLError as exc:
            raise SecretError(f"Vault store failed: {exc}") from exc

    def fetch(self, name: str) -> SecretRecord | None:
        req = urllib.request.Request(
            self._url(name), headers=self._headers(), method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise SecretError(f"Vault fetch failed: {exc}") from exc
        except urllib.error.URLError as exc:
            raise SecretError(f"Vault fetch failed: {exc}") from exc
        return SecretRecord(name=name, ciphertext=raw, backend="vault")

    def delete(self, name: str) -> bool:
        req = urllib.request.Request(
            self._url(name), headers=self._headers(), method="DELETE"
        )
        try:
            urllib.request.urlopen(req, timeout=self._timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
            raise SecretError(f"Vault delete failed: {exc}") from exc
        return True

    def names(self) -> list[str]:
        req = urllib.request.Request(
            f"{self._base}/secrets", headers=self._headers(), method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                import json

                data = json.loads(resp.read().decode("utf-8"))
            return [d["name"] for d in data] if isinstance(data, list) else []
        except urllib.error.URLError as exc:
            raise SecretError(f"Vault list failed: {exc}") from exc


@dataclass
class SecretAccessLog:
    """Access log entry for a secret read."""

    name: str
    accessed_by: str
    ok: bool


class SecretStore:
    """Encrypted secret store over a pluggable backend.

    Args:
        encryptor: Encryptor for at-rest secrets.
        backend: Where ciphertext is persisted (default: memory).
    """

    def __init__(
        self,
        encryptor: VaultEncryptor,
        backend: SecretBackend | None = None,
    ) -> None:
        self._encryptor = encryptor
        self._backend = backend or MemoryBackend()
        self._log: list[SecretAccessLog] = []

    def put(self, name: str, value: str, accessed_by: str = "system") -> None:
        """Encrypt and store a secret value."""
        ciphertext = self._encryptor.encrypt(value)
        self._backend.store(
            SecretRecord(name=name, ciphertext=ciphertext, backend=self._backend.__class__.__name__)
        )
        self._log.append(SecretAccessLog(name=name, accessed_by=accessed_by, ok=True))

    def get(self, name: str, accessed_by: str = "system") -> str:
        """Retrieve and decrypt a secret value.

        Raises:
            SecretError: If the secret does not exist or fails to decrypt.
        """
        record = self._backend.fetch(name)
        if record is None:
            self._log.append(SecretAccessLog(name=name, accessed_by=accessed_by, ok=False))
            raise SecretError(f"Secret '{name}' not found")
        try:
            plaintext = self._encryptor.decrypt(record.ciphertext)
        except Exception as exc:
            self._log.append(SecretAccessLog(name=name, accessed_by=accessed_by, ok=False))
            raise SecretError(f"Failed to decrypt '{name}': {exc}") from exc
        self._log.append(SecretAccessLog(name=name, accessed_by=accessed_by, ok=True))
        return plaintext

    def delete(self, name: str) -> bool:
        """Delete a secret by name."""
        return self._backend.delete(name)

    def exists(self, name: str) -> bool:
        """Whether a secret is stored."""
        return self._backend.fetch(name) is not None

    def list_names(self) -> list[str]:
        """List stored secret names (names only, never values)."""
        return self._backend.names()

    def access_log(self) -> list[SecretAccessLog]:
        """Return the access log (read-only copy)."""
        return list(self._log)


__all__ = [
    "EnvBackend",
    "KeychainBackend",
    "MemoryBackend",
    "RemoteVaultBackend",
    "SecretAccessLog",
    "SecretBackend",
    "SecretError",
    "SecretRecord",
    "SecretStore",
]
