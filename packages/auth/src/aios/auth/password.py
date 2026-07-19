"""Password hashing — bcrypt-based password hashing and verification."""

from __future__ import annotations

import re

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: Plaintext password to hash.

    Returns:
        Bcrypt hash string.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        password: Plaintext password to verify.
        hashed_password: Bcrypt hash to verify against.

    Returns:
        True if the password matches the hash.
    """
    try:
        password_bytes = password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def check_password_strength(password: str) -> dict[str, object]:
    """Check password strength and return issues.

    Args:
        password: Password to check.

    Returns:
        Dictionary with is_strong, errors, strength, score.
    """
    issues: list[str] = []
    score = 0

    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    else:
        score += 1

    if len(password) >= 12:
        score += 1

    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    else:
        score += 1

    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    else:
        score += 1

    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    else:
        score += 1

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")
    else:
        score += 1

    strength = "weak"
    if score >= 5:
        strength = "strong"
    elif score >= 4:
        strength = "medium"
    elif score >= 3:
        strength = "fair"

    return {
        "strength": strength,
        "score": score,
        "max_score": 6,
        "is_strong": score >= 5,
        "errors": issues,
    }
