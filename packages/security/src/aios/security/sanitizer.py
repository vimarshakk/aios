"""Input sanitization utilities for security hardening."""

from __future__ import annotations

import re
from pathlib import PurePosixPath


def sanitize_html(text: str) -> str:
    """Strip HTML tags from a string.

    This is a basic sanitizer — for full HTML sanitization use a dedicated
    library like ``bleach``.
    """
    return re.sub(r"<[^>]+>", "", text)


def sanitize_path(path: str) -> str:
    """Normalize a file path and block path traversal.

    Raises ValueError if the path contains ``..`` components.
    """
    p = PurePosixPath(path)
    parts = p.parts
    if ".." in parts:
        raise ValueError(f"Path traversal not allowed: {path}")
    return str(PurePosixPath(*parts)) if parts else ""


_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def validate_email(email: str) -> bool:
    """Return True if the email address matches a basic pattern."""
    return bool(_EMAIL_RE.match(email.strip()))
