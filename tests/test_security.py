"""Tests for AIOS Security — M2.4 Security Hardening."""

from __future__ import annotations

import tempfile
import time

import pytest

from aios.security.audit import AuditEvent, AuditLevel, AuditLogger
from aios.security.encryption import DecryptError, VaultEncryptor
from aios.security.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    SlidingWindowLimiter,
)
from aios.security.sanitizer import sanitize_html, sanitize_path, validate_email

# ─────────────────────────────────────────────
# Rate Limiter — Token Bucket
# ─────────────────────────────────────────────


class TestTokenBucketLimiter:
    def test_allows_within_capacity(self):
        rl = RateLimiter(capacity=5, refill_rate=100)
        assert rl.allow(3)
        assert rl.allow(2)

    def test_deny_raises_on_exceeded(self):
        rl = RateLimiter(capacity=2, refill_rate=0.1)
        rl.allow(2)
        with pytest.raises(RateLimitExceeded):
            rl.deny(1)

    def test_refill_over_time(self):
        rl = RateLimiter(capacity=3, refill_rate=100.0)
        rl.allow(3)
        assert not rl.allow(1)
        time.sleep(0.02)
        assert rl.allow(1)

    def test_reset(self):
        rl = RateLimiter(capacity=2, refill_rate=0.1)
        rl.allow(2)
        rl.reset()
        assert rl.allow(2)

    def test_remaining_property(self):
        rl = RateLimiter(capacity=5, refill_rate=100)
        rl.allow(2)
        assert rl.remaining == pytest.approx(3.0, abs=0.5)

    def test_cost_one_default(self):
        rl = RateLimiter(capacity=1, refill_rate=100)
        assert rl.allow()
        assert not rl.allow()


# ─────────────────────────────────────────────
# Rate Limiter — Sliding Window
# ─────────────────────────────────────────────


class TestSlidingWindowLimiter:
    def test_allows_within_limit(self):
        sw = SlidingWindowLimiter(max_requests=3, window_seconds=1.0)
        assert sw.allow()
        assert sw.allow()
        assert sw.allow()
        assert not sw.allow()

    def test_window_expiry(self):
        sw = SlidingWindowLimiter(max_requests=2, window_seconds=0.05)
        sw.allow()
        sw.allow()
        assert not sw.allow()
        time.sleep(0.06)
        assert sw.allow()

    def test_deny_raises(self):
        sw = SlidingWindowLimiter(max_requests=1, window_seconds=60)
        sw.allow()
        with pytest.raises(RateLimitExceeded):
            sw.deny()

    def test_current_count(self):
        sw = SlidingWindowLimiter(max_requests=5, window_seconds=1.0)
        sw.allow()
        sw.allow()
        assert sw.current_count == 2

    def test_reset(self):
        sw = SlidingWindowLimiter(max_requests=2, window_seconds=60)
        sw.allow()
        sw.reset()
        assert sw.current_count == 0

    def test_cost_multiple(self):
        sw = SlidingWindowLimiter(max_requests=5, window_seconds=60)
        assert sw.allow(3)
        assert sw.allow(2)
        assert not sw.allow(1)


# ─────────────────────────────────────────────
# Audit Logger
# ─────────────────────────────────────────────


class TestAuditLogger:
    def test_log_and_query(self):
        al = AuditLogger()
        al.log("plugin.install", actor="user1", target="plugin-x")
        events = al.query(action="plugin.install")
        assert len(events) == 1
        assert events[0].actor == "user1"

    def test_query_by_actor(self):
        al = AuditLogger()
        al.log("a", actor="alice")
        al.log("b", actor="bob")
        assert len(al.query(actor="alice")) == 1
        assert len(al.query(actor="bob")) == 1

    def test_query_by_level(self):
        al = AuditLogger()
        al.log("a", level=AuditLevel.INFO)
        al.log("b", level=AuditLevel.ERROR)
        assert al.count(level=AuditLevel.ERROR) == 1

    def test_count(self):
        al = AuditLogger()
        al.log("a")
        al.log("b")
        al.log("c")
        assert al.count() == 3

    def test_clear(self):
        al = AuditLogger()
        al.log("a")
        al.clear()
        assert al.count() == 0

    def test_event_to_json(self):
        al = AuditLogger()
        ev = al.log("test", details={"key": "val"})
        j = ev.to_json()
        assert '"action": "test"' in j
        assert '"key": "val"' in j

    def test_event_to_dict(self):
        ev = AuditEvent(action="x", level=AuditLevel.WARNING)
        d = ev.to_dict()
        assert d["level"] == "warning"

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            path = f"{td}/audit.jsonl"
            al1 = AuditLogger(storage_path=path)
            al1.log("persist_test")
            del al1

            al2 = AuditLogger(storage_path=path)
            assert al2.count() == 1

    def test_limit_query(self):
        al = AuditLogger()
        for i in range(5):
            al.log(f"event_{i}")
        results = al.query(limit=3)
        assert len(results) == 3

    def test_success_flag(self):
        al = AuditLogger()
        al.log("fail_op", success=False)
        assert al.events[0].success is False


# ─────────────────────────────────────────────
# Encryption
# ─────────────────────────────────────────────


class TestVaultEncryptor:
    def test_encrypt_decrypt_roundtrip(self):
        enc = VaultEncryptor.generate_key()
        token = enc.encrypt("hello world")
        assert enc.decrypt(token) == "hello world"

    def test_different_tokens_per_call(self):
        enc = VaultEncryptor.generate_key()
        t1 = enc.encrypt("same")
        t2 = enc.encrypt("same")
        assert t1 != t2  # Different salt each time

    def test_from_password(self):
        enc = VaultEncryptor.from_password("secret")
        token = enc.encrypt("data")
        assert enc.decrypt(token) == "data"

    def test_decrypt_invalid_token(self):
        enc = VaultEncryptor.generate_key()
        with pytest.raises(DecryptError):
            enc.decrypt("not-valid-base64!!!")

    def test_decrypt_too_short(self):
        enc = VaultEncryptor.generate_key()
        import base64
        short = base64.b64encode(b"abc").decode()
        with pytest.raises(DecryptError):
            enc.decrypt(short)

    def test_wrong_key_fails(self):
        enc1 = VaultEncryptor.generate_key()
        enc2 = VaultEncryptor.generate_key()
        token = enc1.encrypt("secret")
        with pytest.raises(DecryptError):
            enc2.decrypt(token)

    def test_empty_string(self):
        enc = VaultEncryptor.generate_key()
        assert enc.decrypt(enc.encrypt("")) == ""

    def test_unicode(self):
        enc = VaultEncryptor.generate_key()
        text = "Hello 🌍 — こんにちは"
        assert enc.decrypt(enc.encrypt(text)) == text

    def test_encrypt_field(self):
        enc = VaultEncryptor.generate_key()
        token = enc.encrypt_field("ssn-value", "ssn")
        assert enc.decrypt_field(token, "ssn") == "ssn-value"

    def test_decrypt_field_wrong_name(self):
        enc = VaultEncryptor.generate_key()
        token = enc.encrypt_field("val", "field_a")
        with pytest.raises(DecryptError):
            enc.decrypt_field(token, "field_b")


# ─────────────────────────────────────────────
# Sanitizer
# ─────────────────────────────────────────────


class TestSanitizer:
    def test_sanitize_html_strips_tags(self):
        assert sanitize_html("<b>hello</b>") == "hello"

    def test_sanitize_html_nested(self):
        assert sanitize_html("<div><span>test</span></div>") == "test"

    def test_sanitize_html_no_tags(self):
        assert sanitize_html("plain text") == "plain text"

    def test_sanitize_path_valid(self):
        assert sanitize_path("foo/bar/baz") == "foo/bar/baz"

    def test_sanitize_path_traversal_blocked(self):
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            sanitize_path("foo/../../../etc/passwd")

    def test_sanitize_path_dotdot_in_middle(self):
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            sanitize_path("a/b/../c")

    def test_validate_email_valid(self):
        assert validate_email("user@example.com")
        assert validate_email("test.name+tag@domain.co")

    def test_validate_email_invalid(self):
        assert not validate_email("not-an-email")
        assert not validate_email("@no-user.com")
        assert not validate_email("user@.com")
