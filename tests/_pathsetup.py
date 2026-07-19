"""Shared sys.path bootstrap for AIOS smoke/integration scripts.

Adds every aios package's `src/` directory to sys.path so that
`import aios.X` works without an editable install. Imported for side effects.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_PKG_DIRS = [
    "packages/core/src",
    "packages/agents/src",
    "packages/orchestrator/src",
    "packages/memory/src",
    "packages/tools/src",
    "packages/providers/src",
    "packages/supervisor/src",
    "packages/platform/src",
    "services/gateway/src",
    "services/supervisor/src",
]

for rel in _PKG_DIRS:
    d = ROOT / rel
    if d.is_dir() and str(d) not in sys.path:
        sys.path.insert(0, str(d))

# Repo root + tests dir so local test fixtures (e.g. test_supervisor._FakePlatform) import
for d in (ROOT, ROOT / "tests"):
    if d.is_dir() and str(d) not in sys.path:
        sys.path.insert(0, str(d))
