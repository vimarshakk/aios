"""MemoryIO — import/export memory data in JSON and Markdown formats.

Supports:
- Export: JSON, Markdown
- Import: JSON, Markdown
- Full workspace export/import
- Selective export (by type, time range, tags)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from aios.memory.entity import Entity, EntityMemory
from aios.memory.episodic import Episode, EpisodicMemory
from aios.memory.fact_store import Fact, FactStore
from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph
from aios.memory.vector_light import LightweightVectorMemory


@dataclass
class ExportResult:
    """Result of an export operation."""

    format: str  # "json" or "markdown"
    content: str
    episode_count: int = 0
    entity_count: int = 0
    fact_count: int = 0
    graph_node_count: int = 0
    graph_edge_count: int = 0
    size_bytes: int = 0


@dataclass
class ImportResult:
    """Result of an import operation."""

    format: str
    episodes_imported: int = 0
    entities_imported: int = 0
    facts_imported: int = 0
    graph_nodes_imported: int = 0
    graph_edges_imported: int = 0
    errors: list[str] = field(default_factory=list)


class MemoryIO:
    """Import/export memory data in JSON and Markdown formats.

    Usage:
        io = MemoryIO(episodic, entity_mem, fact_store, graph, vector)
        result = io.export_json()
        result = io.export_markdown()
        import_result = await io.import_json(result.content)
        import_result = await io.import_markdown(result.content)
    """

    def __init__(
        self,
        episodic: EpisodicMemory | None = None,
        entity_memory: EntityMemory | None = None,
        fact_store: FactStore | None = None,
        graph: KnowledgeGraph | None = None,
        vector_memory: LightweightVectorMemory | None = None,
    ) -> None:
        self._episodic = episodic
        self._entity_memory = entity_memory
        self._fact_store = fact_store
        self._graph = graph
        self._vector = vector_memory

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(
        self,
        *,
        include_episodes: bool = True,
        include_entities: bool = True,
        include_facts: bool = True,
        include_graph: bool = True,
        include_vectors: bool = True,
    ) -> ExportResult:
        """Export all memory data as JSON."""
        data: dict[str, Any] = {
            "version": "1.0",
            "exported_at": time.time(),
            "format": "aios-memory-json",
        }
        counts = ExportResult(format="json", content="")

        if include_episodes and self._episodic:
            episodes = self._episodic.get_recent(n=10000)
            data["episodes"] = [
                {
                    "id": ep.id,
                    "content": ep.content,
                    "timestamp": ep.timestamp,
                    "session_id": ep.session_id,
                    "tags": ep.tags,
                    "metadata": ep.metadata,
                }
                for ep in episodes
            ]
            counts.episode_count = len(episodes)

        if include_entities and self._entity_memory:
            entities = self._entity_memory.get_entities_by_type("person")
            entities += self._entity_memory.get_entities_by_type("place")
            entities += self._entity_memory.get_entities_by_type("thing")
            entities += self._entity_memory.get_entities_by_type("concept")
            entities += self._entity_memory.get_entities_by_type("entity")
            # Deduplicate
            seen = set()
            unique = []
            for e in entities:
                if e.id not in seen:
                    seen.add(e.id)
                    unique.append(e)
            data["entities"] = [
                {
                    "id": e.id,
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "attributes": e.attributes,
                    "relationships": e.relationships,
                }
                for e in unique
            ]
            counts.entity_count = len(unique)

        if include_facts and self._fact_store:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    facts = []
                else:
                    facts = loop.run_until_complete(self._fact_store.list_all())
            except RuntimeError:
                facts = []
            data["facts"] = [
                {
                    "id": f.id,
                    "subject": f.subject,
                    "predicate": f.predicate,
                    "obj": f.obj,
                    "confidence": f.confidence,
                    "source": f.source,
                }
                for f in facts
            ]
            counts.fact_count = len(facts)

        if include_graph and self._graph:
            nodes = self._graph.list_nodes()
            edges = self._graph.list_edges()
            data["graph"] = {
                "nodes": [
                    {
                        "id": n.id,
                        "label": n.label,
                        "node_type": n.node_type,
                        "properties": n.properties,
                    }
                    for n in nodes
                ],
                "edges": [
                    {
                        "id": e.id,
                        "source_id": e.source_id,
                        "target_id": e.target_id,
                        "relation": e.relation,
                        "weight": e.weight,
                        "properties": e.properties,
                    }
                    for e in edges
                ],
            }
            counts.graph_node_count = len(nodes)
            counts.graph_edge_count = len(edges)

        if include_vectors and self._vector:
            data["vectors"] = self._vector.export_all()

        content = json.dumps(data, indent=2, default=str)
        counts.content = content
        counts.size_bytes = len(content.encode("utf-8"))
        return counts

    def export_markdown(
        self,
        *,
        include_episodes: bool = True,
        include_entities: bool = True,
        include_facts: bool = True,
        include_graph: bool = True,
    ) -> ExportResult:
        """Export memory data as Markdown."""
        lines: list[str] = []
        lines.append("# AIOS Memory Export")
        lines.append(f"\n*Exported at: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n")
        counts = ExportResult(format="markdown", content="")

        if include_episodes and self._episodic:
            episodes = self._episodic.get_recent(n=10000)
            lines.append(f"## Episodes ({len(episodes)})\n")
            for ep in episodes[-50:]:  # Last 50 in markdown
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(ep.timestamp))
                tags = f" [{', '.join(ep.tags)}]" if ep.tags else ""
                lines.append(f"### {ts}{tags}")
                lines.append(f"\n{ep.content}\n")
            counts.episode_count = len(episodes)

        if include_entities and self._entity_memory:
            all_entities = (
                self._entity_memory.get_entities_by_type("person")
                + self._entity_memory.get_entities_by_type("place")
                + self._entity_memory.get_entities_by_type("thing")
                + self._entity_memory.get_entities_by_type("concept")
                + self._entity_memory.get_entities_by_type("entity")
            )
            seen = set()
            unique = [e for e in all_entities if e.id not in seen and not seen.add(e.id)]
            lines.append(f"\n## Entities ({len(unique)})\n")
            for e in unique:
                attrs = ", ".join(f"{k}={v}" for k, v in e.attributes.items()) if e.attributes else "none"
                rels = "; ".join(f"{r['relation']}→{r['target']}" for r in e.relationships[:5]) if e.relationships else "none"
                lines.append(f"- **{e.name}** ({e.entity_type}): {attrs}")
                if rels != "none":
                    lines.append(f"  - Relations: {rels}")
            counts.entity_count = len(unique)

        if include_facts and self._fact_store:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                facts = [] if loop.is_running() else loop.run_until_complete(self._fact_store.list_all())
            except RuntimeError:
                facts = []
            lines.append(f"\n## Facts ({len(facts)})\n")
            for f in facts:
                lines.append(f"- {f.subject} **{f.predicate}** {f.obj} (conf: {f.confidence:.2f})")
            counts.fact_count = len(facts)

        if include_graph and self._graph:
            nodes = self._graph.list_nodes()
            edges = self._graph.list_edges()
            lines.append(f"\n## Knowledge Graph\n")
            lines.append(f"**Nodes:** {len(nodes)} | **Edges:** {len(edges)}\n")
            for n in nodes[:30]:
                out_edges = self._graph.get_outgoing_edges(n.id)
                rels = [f"→{self._graph.get_node(e.target_id).label if self._graph.get_node(e.target_id) else '?'} ({e.relation})" for e in out_edges[:3]]
                lines.append(f"- {n.label} ({n.node_type}): {', '.join(rels)}" if rels else f"- {n.label} ({n.node_type})")
            counts.graph_node_count = len(nodes)
            counts.graph_edge_count = len(edges)

        content = "\n".join(lines)
        counts.content = content
        counts.size_bytes = len(content.encode("utf-8"))
        return counts

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    async def import_json(self, content: str) -> ImportResult:
        """Import memory data from JSON."""
        result = ImportResult(format="json")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON: {e}")
            return result

        if data.get("format") != "aios-memory-json":
            result.errors.append(f"Unknown format: {data.get('format')}")
            return result

        # Import episodes
        for ep_data in data.get("episodes", []):
            try:
                if self._episodic:
                    await self._episodic.store(
                        ep_data["content"],
                        metadata={
                            "timestamp": ep_data.get("timestamp", time.time()),
                            "session_id": ep_data.get("session_id", ""),
                            "tags": ep_data.get("tags", []),
                            **ep_data.get("metadata", {}),
                        },
                    )
                    result.episodes_imported += 1
            except Exception as e:
                result.errors.append(f"Episode import error: {e}")

        # Import entities
        for ent_data in data.get("entities", []):
            try:
                if self._entity_memory:
                    await self._entity_memory.store(
                        ent_data["name"],
                        metadata={
                            "entity_name": ent_data["name"],
                            "entity_type": ent_data.get("entity_type", "entity"),
                            **ent_data.get("attributes", {}),
                        },
                    )
                    result.entities_imported += 1
            except Exception as e:
                result.errors.append(f"Entity import error: {e}")

        # Import facts
        for fact_data in data.get("facts", []):
            try:
                if self._fact_store:
                    fact = Fact(
                        id=fact_data.get("id", f"import_{uuid.uuid4().hex[:8]}"),
                        subject=fact_data["subject"],
                        predicate=fact_data["predicate"],
                        obj=fact_data["obj"],
                        confidence=fact_data.get("confidence", 0.8),
                        source=fact_data.get("source", "import"),
                    )
                    await self._fact_store.store(fact)
                    result.facts_imported += 1
            except Exception as e:
                result.errors.append(f"Fact import error: {e}")

        # Import graph
        graph_data = data.get("graph", {})
        for node_data in graph_data.get("nodes", []):
            try:
                if self._graph:
                    node = GraphNode(
                        id=node_data["id"],
                        label=node_data["label"],
                        node_type=node_data.get("node_type", "entity"),
                        properties=node_data.get("properties", {}),
                    )
                    self._graph.add_node(node)
                    result.graph_nodes_imported += 1
            except Exception as e:
                result.errors.append(f"Graph node import error: {e}")

        for edge_data in graph_data.get("edges", []):
            try:
                if self._graph:
                    edge = GraphEdge(
                        id=edge_data["id"],
                        source_id=edge_data["source_id"],
                        target_id=edge_data["target_id"],
                        relation=edge_data.get("relation", "related"),
                        weight=edge_data.get("weight", 1.0),
                        properties=edge_data.get("properties", {}),
                    )
                    self._graph.add_edge(edge)
                    result.graph_edges_imported += 1
            except Exception as e:
                result.errors.append(f"Graph edge import error: {e}")

        return result

    async def import_markdown(self, content: str) -> ImportResult:
        """Import memory data from Markdown (episodes and entities only)."""
        result = ImportResult(format="markdown")
        lines = content.split("\n")

        current_section = ""
        current_content: list[str] = []

        for line in lines:
            if line.startswith("## "):
                # Process previous section
                if current_section and current_content:
                    self._process_markdown_section(
                        current_section, "\n".join(current_content), result
                    )
                current_section = line[3:].strip()
                current_content = []
            elif line.startswith("### "):
                # Episode header — store previous episode
                if current_content and self._episodic:
                    text = "\n".join(current_content).strip()
                    if text:
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if not loop.is_running():
                                loop.run_until_complete(
                                    self._episodic.store(text, metadata={"source": "markdown_import"})
                                )
                                result.episodes_imported += 1
                        except RuntimeError:
                            pass
                current_content = []
            else:
                current_content.append(line)

        # Process last section
        if current_section and current_content:
            self._process_markdown_section(
                current_section, "\n".join(current_content), result
            )

        return result

    def _process_markdown_section(
        self,
        section: str,
        content: str,
        result: ImportResult,
    ) -> None:
        """Process a markdown section for entity/fact extraction."""
        if "Entit" in section:
            # Parse entity lines: "- **Name** (type): attrs"
            for line in content.split("\n"):
                match = re.match(r"^-\s+\*\*(.+?)\*\*\s+\((.+?)\)", line)
                if match and self._entity_memory:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if not loop.is_running():
                            loop.run_until_complete(
                                self._entity_memory.store(
                                    match.group(1),
                                    metadata={
                                        "entity_name": match.group(1),
                                        "entity_type": match.group(2),
                                    },
                                )
                            )
                            result.entities_imported += 1
                    except RuntimeError:
                        pass
        elif "Fact" in section:
            # Parse fact lines: "- subject **predicate** object (conf: 0.80)"
            for line in content.split("\n"):
                match = re.match(r"^-\s+(.+?)\s+\*\*(.+?)\*\*\s+(.+?)\s+\(conf:", line)
                if match and self._fact_store:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if not loop.is_running():
                            from aios.memory.fact_store import Fact as FactCls
                            import uuid as _uuid
                            fact = FactCls(
                                id=f"md_{_uuid.uuid4().hex[:8]}",
                                subject=match.group(1),
                                predicate=match.group(2),
                                obj=match.group(3),
                                confidence=0.8,
                                source="markdown_import",
                            )
                            loop.run_until_complete(self._fact_store.store(fact))
                            result.facts_imported += 1
                    except RuntimeError:
                        pass


import uuid  # needed for import_markdown fact IDs


__all__ = [
    "ExportResult",
    "ImportResult",
    "MemoryIO",
]
