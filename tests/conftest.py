"""Shared pytest configuration for the AIOS test suite."""

from __future__ import annotations

import importlib
import os
import pytest


# ---------------------------------------------------------------------------
# Skip tests that require `aios.*` subpackages when not installed.
# ---------------------------------------------------------------------------

def _aios_available() -> bool:
    """Return True if the aios package can be imported."""
    try:
        importlib.import_module("aios")
        return True
    except (ImportError, ModuleNotFoundError):
        return False


if not _aios_available():
    # When aios is not installed, skip all test files that import from it.
    # M16/M17 milestone tests are self-contained (read source files directly)
    # and don't need aios installed, so they keep running.
    _tests_dir = os.path.dirname(__file__)
    _all_test_files = [
        os.path.join(_tests_dir, f)
        for f in os.listdir(_tests_dir)
        if f.startswith("test_") and f.endswith(".py")
    ]
    # Keep only M16/M17 milestone tests (they read source directly, no aios imports)
    _milestone_prefixes = ("test_m16_", "test_m17_")
    _keep = [
        f for f in _all_test_files
        if os.path.basename(f).startswith(_milestone_prefixes)
    ]
    _skip = [f for f in _all_test_files if f not in _keep]

    collect_ignore = _skip  # type: ignore[assignment]
else:
    collect_ignore = []  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Standard hooks
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """Deselect live-network tests by default.

    Tests marked ``network`` reach external hosts (httpbin.org) and are
    flaky/hang-prone depending on egress. Opt in explicitly with
    ``-m network`` when intentionally exercising them.
    """
    if config.getoption("-m"):
        return
    skip = pytest.mark.skip(reason="network tests deselected (use '-m network')")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "network: marks tests that require live network egress"
    )
