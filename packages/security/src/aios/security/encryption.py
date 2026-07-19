"""Encryption utilities — symmetric encryption for data at rest."""

from __future__ import annotations

import base64
import hashlib
import itertools
import secrets
from dataclasses import dataclass


class EncryptError(Exception):
    """Raised when encryption fails."""


class DecryptError(Exception):
    """Raised when decryption fails."""


@dataclass(frozen=True, slots=True)
class VaultEncryptor:
    """Simple XOR-based symmetric encryptor for development.

    In production, this should be replaced with AES-GCM via the
    ``cryptography`` library. This implementation provides the same
    interface for testing and development without native dependencies.

    Attributes:
        key: Encryption key (bytes or hex string).
    """

    key: bytes

    @classmethod
    def from_password(cls, password: str, salt: bytes | None = None) -> VaultEncryptor:
        """Derive an encryption key from a password using PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return cls(key=dk)

    @classmethod
    def generate_key(cls) -> VaultEncryptor:
        """Generate a random 32-byte encryption key."""
        return cls(key=secrets.token_bytes(32))

    def _derive_stream(self, salt: bytes, length: int) -> bytes:
        """Derive a keystream of the exact needed length by cycling PBKDF2 output."""
        derived = hashlib.pbkdf2_hmac("sha256", self.key, salt, 1)
        if len(derived) >= length:
            return derived[:length]
        return bytes(itertools.islice(itertools.cycle(derived), length))

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return a base64-encoded token.

        Format: ``base64(salt + ciphertext)``
        """
        # Prefix with a magic string to detect wrong keys/corruption on decryption
        plaintext_bytes = b"AIOS" + plaintext.encode("utf-8")
        salt = secrets.token_bytes(16)
        keystream = self._derive_stream(salt, len(plaintext_bytes))
        ciphertext = bytes(
            p ^ k for p, k in zip(plaintext_bytes, keystream, strict=True)
        )
        return base64.b64encode(salt + ciphertext).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decrypt a base64-encoded token back to plaintext."""
        try:
            raw = base64.b64decode(token)
        except Exception as exc:
            raise DecryptError(f"Invalid token: {exc}") from exc

        if len(raw) < 16:
            raise DecryptError("Token too short")

        salt = raw[:16]
        ciphertext = raw[16:]
        keystream = self._derive_stream(salt, len(ciphertext))
        plaintext_bytes = bytes(
            c ^ k for c, k in zip(ciphertext, keystream, strict=True)
        )
        if not plaintext_bytes.startswith(b"AIOS"):
            raise DecryptError("Decryption produced invalid data (wrong key?)")
        try:
            return plaintext_bytes[4:].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DecryptError("Decryption produced invalid data (wrong key?)") from exc

    def encrypt_field(self, value: str, field_name: str) -> str:
        """Encrypt a specific field with a context binding."""
        bound = f"{field_name}:{value}"
        return self.encrypt(bound)

    def decrypt_field(self, token: str, field_name: str) -> str:
        """Decrypt a context-bound field."""
        bound = self.decrypt(token)
        prefix = f"{field_name}:"
        if not bound.startswith(prefix):
            raise DecryptError(
                f"Field name mismatch: expected '{field_name}'"
            )
        return bound[len(prefix):]
