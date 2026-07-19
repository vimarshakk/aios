"""AIOS Memory — unified memory API with pluggable backends."""

from aios.memory.backend import MemoryBackend, RetrievalResult
from aios.memory.cache import CacheMemory
from aios.memory.consolidator import ConsolidationResult, MemoryConsolidator
from aios.memory.entity import Entity, EntityMemory
from aios.memory.episodic import Episode, EpisodicMemory
from aios.memory.events import MemoryEvent, MemoryEventType
from aios.memory.fact_store import Fact, FactStore, JSONLFactStore
from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph
from aios.memory.graph_query import GraphQuery, PatternMatch
from aios.memory.long_term import LongTermMemory
from aios.memory.manager import BackendConfig, HybridMemoryManager
from aios.memory.short_term import ShortTermMemory

API_VERSION = "1.0"

__all__ = [
    "BackendConfig",
    "CacheMemory",
    "ConsolidationResult",
    "Entity",
    "EntityMemory",
    "Episode",
    "EpisodicMemory",
    "Fact",
    "FactStore",
    "GraphEdge",
    "GraphNode",
    "GraphQuery",
    "HybridMemoryManager",
    "JSONLFactStore",
    "KnowledgeGraph",
    "LongTermMemory",
    "MemoryBackend",
    "MemoryConsolidator",
    "MemoryEvent",
    "MemoryEventType",
    "PatternMatch",
    "RetrievalResult",
    "ShortTermMemory",
]
