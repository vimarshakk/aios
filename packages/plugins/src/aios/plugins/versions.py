"""SemVer parsing and version range matching for the plugin marketplace."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SemVer:
    """Semantic version with major.minor.patch.

    Supports comparison operators and ``__str__``.
    """

    major: int = 0
    minor: int = 0
    patch: int = 0

    # -- parsing -----------------------------------------------------------

    @classmethod
    def parse(cls, version: str) -> SemVer:
        """Parse a semver string like ``1.2.3`` or ``v1.2.3``."""
        v = version.lstrip("v").strip()
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v)
        if not match:
            raise ValueError(f"Invalid semver: {version!r}")
        return cls(int(match[1]), int(match[2]), int(match[3]))

    # -- comparison --------------------------------------------------------

    def __lt__(self, other: SemVer) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other: SemVer) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch) <= (
            other.major,
            other.minor,
            other.patch,
        )

    def __gt__(self, other: SemVer) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        )

    def __ge__(self, other: SemVer) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch) >= (
            other.major,
            other.minor,
            other.patch,
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class VersionRange:
    """A version range expression (e.g. ``>=1.0.0 <2.0.0``, ``^1.2.0``, ``~1.3.0``).

    Supports three forms:
        - Explicit range: ``>=1.0.0 <2.0.0`` (space-separated)
        - Caret: ``^1.2.0`` means ``>=1.2.0 <2.0.0``
        - Tilde: ``~1.3.0`` means ``>=1.3.0 <1.4.0``
        - Exact: ``1.2.3`` means ``==1.2.3``
    """

    expression: str

    # -- matching ----------------------------------------------------------

    def matches(self, version: SemVer) -> bool:
        """Return True if *version* satisfies this range."""
        expr = self.expression.strip()

        # Caret range: ^1.2.3 → >=1.2.3 <2.0.0
        if expr.startswith("^"):
            base = SemVer.parse(expr[1:])
            return version >= base and version.major == base.major

        # Tilde range: ~1.3.0 → >=1.3.0 <1.4.0
        if expr.startswith("~"):
            base = SemVer.parse(expr[1:])
            return (
                version >= base
                and version.major == base.major
                and version.minor == base.minor
            )

        # Space-separated range: >=1.0.0 <2.0.0
        parts = expr.split()
        if len(parts) >= 2 and all(
            p[:1] in (">", "<", "=") for p in parts
        ):
            return all(self._matches_single(p, version) for p in parts)

        # Exact match
        return version == SemVer.parse(expr)

    @staticmethod
    def _matches_single(part: str, version: SemVer) -> bool:
        part = part.strip()
        if part.startswith(">="):
            return version >= SemVer.parse(part[2:])
        if part.startswith("<="):
            return version <= SemVer.parse(part[2:])
        if part.startswith(">"):
            return version > SemVer.parse(part[1:])
        if part.startswith("<"):
            return version < SemVer.parse(part[1:])
        if part.startswith("="):
            return version == SemVer.parse(part[1:])
        return version == SemVer.parse(part)


def is_compatible(installed: str, required: str) -> bool:
    """Check if an installed version satisfies a required range."""
    return VersionRange(required).matches(SemVer.parse(installed))
