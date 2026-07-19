"""AIOS Security — Rate limiting, audit logging, encryption, and input validation."""

from __future__ import annotations

from aios.security.audit import AuditEvent, AuditLevel, AuditLogger
from aios.security.encryption import DecryptError, EncryptError, VaultEncryptor
from aios.security.rate_limiter import RateLimiter, RateLimitExceeded, SlidingWindowLimiter
from aios.security.sanitizer import sanitize_html, sanitize_path, validate_email

API_VERSION = "1.0"

TokenBucketLimiter = RateLimiter
RateLimitExceededError = RateLimitExceeded

__all__ = [
    "AuditEvent",
    "AuditLevel",
    "AuditLogger",
    "DecryptError",
    "EncryptError",
    "RateLimitExceeded",
    "RateLimiter",
    "SlidingWindowLimiter",
    "TokenBucketLimiter",
    "VaultEncryptor",
    "sanitize_html",
    "sanitize_path",
    "validate_email",
]
