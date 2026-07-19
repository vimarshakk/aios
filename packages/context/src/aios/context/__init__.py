"""AIOS Context Engine — builds rich context for every agent invocation."""

from aios.context.builder import ContextBuilder, ContextSpec
from aios.context.inject import inject_context
from aios.context.ranking import RelevanceRanker, ScoredResult
from aios.context.retriever import MemoryRetriever, RetrievalResult
from aios.context.summarizer import ContextSummarizer
from aios.context.window import ConversationWindow

API_VERSION = "1.0"

__all__ = [
    "ContextBuilder",
    "ContextSpec",
    "ContextSummarizer",
    "ConversationWindow",
    "MemoryRetriever",
    "RelevanceRanker",
    "RetrievalResult",
    "ScoredResult",
    "inject_context",
]
