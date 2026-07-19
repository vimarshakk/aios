"""Tests for AIOS CLI v2 — interactive mode, plugin commands."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aios.sdk.cli_v2 import v2

runner = CliRunner()


@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


# ─── Plugin Commands ──────────────────────────


class TestPluginCommands:
    def test_plugin_list_empty(self, data_dir):
        result = runner.invoke(v2, ["plugin", "--data-dir", str(data_dir)])
        assert "No plugins installed" in result.output

    def test_plugin_install_success(self, data_dir):
        result = runner.invoke(
            v2,
            ["plugin-install", "test-plugin", "-d", str(data_dir)],
        )
        assert result.exit_code == 0
        assert "Installed" in result.output
        assert "test-plugin" in result.output

    def test_plugin_remove_not_installed(self, data_dir):
        result = runner.invoke(
            v2, ["plugin-remove", "nonexistent", "--data-dir", str(data_dir)],
        )
        assert result.exit_code == 1
        assert "Remove failed" in result.output

    def test_plugin_search_empty(self, data_dir):
        result = runner.invoke(
            v2, ["plugin-search", "zzz-nonexistent", "--data-dir", str(data_dir)],
        )
        assert "No plugins found" in result.output

    def test_plugin_search_finds_installed(self, data_dir):
        runner.invoke(
            v2,
            ["plugin-install", "searchable-plugin", "-d", str(data_dir)],
        )
        result = runner.invoke(
            v2, ["plugin-search", "searchable", "--data-dir", str(data_dir)],
        )
        assert "searchable-plugin" in result.output


# ─── Version Commands ─────────────────────────


class TestVersionCommands:
    def test_version_check_compatible(self):
        from aios.plugins.versions import SemVer, VersionRange, is_compatible

        sem = SemVer.parse("1.5.0")
        vr = VersionRange(expression=">=1.0.0 <2.0.0")
        assert is_compatible(str(sem), vr.expression)

    def test_version_check_incompatible(self):
        from aios.plugins.versions import SemVer, VersionRange, is_compatible

        sem = SemVer.parse("0.9.0")
        vr = VersionRange(expression=">=1.0.0 <2.0.0")
        assert not is_compatible(str(sem), vr.expression)

    def test_version_compare_less(self):
        from aios.plugins.versions import SemVer

        assert SemVer.parse("1.0.0") < SemVer.parse("2.0.0")

    def test_version_compare_equal(self):
        from aios.plugins.versions import SemVer

        assert SemVer.parse("1.0.0") == SemVer.parse("1.0.0")

    def test_version_compare_greater(self):
        from aios.plugins.versions import SemVer

        assert SemVer.parse("2.0.0") > SemVer.parse("1.0.0")

    def test_cli_version_compare(self):
        result = runner.invoke(v2, ["version-compare", "1.0.0", "2.0.0"])
        assert "<" in result.output


# ─── Dependency Commands ──────────────────────


class TestDepCommands:
    def test_deps_check_empty(self, data_dir):
        result = runner.invoke(v2, ["deps-check", "--data-dir", str(data_dir)])
        assert "No plugins installed" in result.output


# ─── Security Commands ────────────────────────


class TestSecurityCommands:
    def test_rate_status(self):
        result = runner.invoke(v2, ["rate-status"])
        assert "Token Bucket" in result.output
        assert "Sliding Window" in result.output

    def test_audit_log_empty(self, data_dir):
        result = runner.invoke(v2, ["audit-log", "--data-dir", str(data_dir)])
        assert "No audit events" in result.output


# ─── Interactive Shell ────────────────────────


class TestShell:
    def test_shell_help_and_exit(self):
        result = runner.invoke(v2, ["shell"], input="help\nexit\n")
        assert "Commands:" in result.output
        assert "Goodbye" in result.output

    def test_shell_unknown_command(self):
        result = runner.invoke(v2, ["shell"], input="unknown\nexit\n")
        assert "Unknown command" in result.output

    def test_shell_quit_shortcut(self):
        result = runner.invoke(v2, ["shell"], input="q\n")
        assert "Goodbye" in result.output

    def test_shell_empty_lines_skipped(self):
        result = runner.invoke(v2, ["shell"], input="\n\nexit\n")
        assert "Goodbye" in result.output
