"""AIOS Developer Platform runtime package."""

from aios.platform.platform import AgentRegistration, DeveloperPlatform
from aios.platform.resolver import (
    CapabilityResolver,
    ProviderKind,
    Resolution,
)

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "AgentRegistration",
    "CapabilityResolver",
    "DeveloperPlatform",
    "ProviderKind",
    "Resolution",
]
