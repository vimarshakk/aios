"""EntityMemory — entity-relationship memory for personalization."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from aios.memory.backend import MemoryBackend, RetrievalResult


@dataclass
class Entity:
    """A stored entity with its relationships."""

    id: str
    name: str
    entity_type: str  # "person", "place", "thing", "concept"
    attributes: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, str]] = field(default_factory=list)
    # e.g., [{"relation": "works_at", "target": "Google"}]
    created_at: float = 0.0
    updated_at: float = 0.0


class EntityMemory(MemoryBackend):
    """Entity-relationship memory for tracking people, places, things, and concepts.

    Useful for personalization: "Remember that Priya works at Google"
    or "What do I know about the meeting room?".
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._name_index: dict[str, str] = {}  # lowercase name → entity ID

    async def store(
        self,
        content: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        meta = metadata or {}
        entity_name = meta.pop("entity_name", content[:50])
        entity_type = meta.pop("entity_type", "thing")

        # Check if entity already exists by name
        existing_id = self._name_index.get(entity_name.lower())
        if existing_id and existing_id in self._entities:
            # Update existing entity
            entity = self._entities[existing_id]
            entity.attributes.update(meta)
            entity.updated_at = time.time()
            return existing_id

        doc_id = uuid.uuid4().hex[:12]
        now = time.time()
        entity = Entity(
            id=doc_id,
            name=entity_name,
            entity_type=entity_type,
            attributes=meta,
            created_at=now,
            updated_at=now,
        )
        self._entities[doc_id] = entity
        self._name_index[entity_name.lower()] = doc_id
        return doc_id

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        query_lower = query.lower()
        scored: list[tuple[float, Entity]] = []

        for entity in self._entities.values():
            name_lower = entity.name.lower()

            # Exact name match
            if query_lower == name_lower:
                score = 1.0
            # Name contains query or query contains name
            elif query_lower in name_lower or name_lower in query_lower:
                score = 0.85
            # Type match
            elif entity.entity_type.lower() in query_lower:
                score = 0.6
            # Attribute or relationship match
            elif any(
                query_lower in str(v).lower()
                for v in entity.attributes.values()
            ) or any(
                query_lower in rel.get("target", "").lower()
                for rel in entity.relationships
            ):
                score = 0.5
            else:
                score = 0.0

            if score >= min_score:
                scored.append((score, entity))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            RetrievalResult(
                content=f"{e.name} ({e.entity_type}): {e.attributes}",
                score=s,
                metadata={
                    "entity_name": e.name,
                    "entity_type": e.entity_type,
                    "attributes": e.attributes,
                    "relationships": e.relationships,
                },
                source="entity",
                doc_id=e.id,
                created_at=e.created_at,
            )
            for s, e in scored[:top_k]
        ]

    async def delete(self, doc_id: str) -> bool:
        entity = self._entities.pop(doc_id, None)
        if entity:
            self._name_index.pop(entity.name.lower(), None)
            return True
        return False

    async def clear(self) -> None:
        self._entities.clear()
        self._name_index.clear()

    async def count(self) -> int:
        return len(self._entities)

    async def has(self, doc_id: str) -> bool:
        return doc_id in self._entities

    def get_entity_by_name(self, name: str) -> Entity | None:
        """Look up an entity by name."""
        entity_id = self._name_index.get(name.lower())
        if entity_id:
            return self._entities.get(entity_id)
        return None

    def add_relationship(
        self,
        entity_id: str,
        relation: str,
        target: str,
    ) -> bool:
        """Add a relationship to an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return False
        entity.relationships.append({"relation": relation, "target": target})
        entity.updated_at = time.time()
        return True

    def get_entities_by_type(self, entity_type: str) -> list[Entity]:
        """Return all entities of a given type."""
        return [e for e in self._entities.values() if e.entity_type == entity_type]
