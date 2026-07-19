"""Shared pytest configuration for the AIOS test suite."""

from __future__ import annotations

import pytest


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
