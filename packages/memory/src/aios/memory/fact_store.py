"""Abstract fact store + JSONL implementation.

Extracted from OpenJarvis memory/store.py (Apache 2.0).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fact:
    """A single extracted fact (entity-relation-entity triple)."""
    id: str
    subject: str
    predicate: str
    obj: str
    confidence: float = 1.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class FactStore(ABC):
    """Abstract interface for fact storage and retrieval."""

    @abstractmethod
    async def store(self, fact: Fact) -> None:
        """Persist a fact."""
        ...

    @abstractmethod
    async def query(self, subject: str | None = None, predicate: str | None = None) -> list[Fact]:
        """Retrieve facts matching the given filters."""
        ...

    @abstractmethod
    async def delete(self, fact_id: str) -> bool:
        """Delete a fact by ID."""
        ...

    @abstractmethod
    async def list_all(self) -> list[Fact]:
        """Return all stored facts."""
        ...


class JSONLFactStore(FactStore):
    """Simple file-backed JSONL fact store for local development."""

    def __init__(self, path: str = "facts.jsonl") -> None:
        self._path = path
        self._facts: dict[str, Fact] = {}
        self._load()

    def _load(self) -> None:
        import json
        from pathlib import Path

        if not Path(self._path).exists():
            return
        for line in Path(self._path).read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            fact = Fact(**d)
            self._facts[fact.id] = fact

    def _save(self) -> None:
        import json
        from pathlib import Path

        with Path(self._path).open("w") as f:
            f.writelines(json.dumps({
                    "id": fact.id,
                    "subject": fact.subject,
                    "predicate": fact.predicate,
                    "obj": fact.obj,
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "metadata": fact.metadata,
                }) + "\n" for fact in self._facts.values())

    async def store(self, fact: Fact) -> None:
        self._facts[fact.id] = fact
        self._save()

    async def query(self, subject: str | None = None, predicate: str | None = None) -> list[Fact]:
        results = list(self._facts.values())
        if subject:
            results = [f for f in results if f.subject == subject]
        if predicate:
            results = [f for f in results if f.predicate == predicate]
        return results

    async def delete(self, fact_id: str) -> bool:
        if fact_id in self._facts:
            del self._facts[fact_id]
            self._save()
            return True
        return False

    async def list_all(self) -> list[Fact]:
        return list(self._facts.values())


__all__ = ["Fact", "FactStore", "JSONLFactStore"]
