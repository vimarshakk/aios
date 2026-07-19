# AIOS Context Package

The context package provides rich context building, retrieval, ranking, and summarization for agent invocations.

## Features

- **ContextBuilder** - Build rich context from multiple sources
- **MemoryRetriever** - Retrieve relevant memories for context
- **RelevanceRanker** - Rank context by relevance
- **ContextSummarizer** - Summarize context for token efficiency
- **ConversationWindow** - Manage conversation history windows

## Quick Start

```python
from aios.context import ContextBuilder, ContextSpec

# Build context for an agent
builder = ContextBuilder()
context = await builder.build(
    ContextSpec(
        query="What are Python async patterns?",
        max_tokens=4000,
        include_memory=True,
        include_conversation=True,
    )
)
print(context)
```

## Context Sources

```python
# Combine multiple context sources
context = await builder.build(
    ContextSpec(
        query="Research topic",
        sources=[
            "memory",
            "conversation",
            "documents",
            "web",
        ],
        max_tokens=8000,
    )
)
```

## Relevance Ranking

```python
from aios.context import RelevanceRanker

ranker = RelevanceRanker()

# Rank context by relevance to query
ranked = await ranker.rank(
    query="Python async patterns",
    documents=documents,
    top_k=5
)
```

## Documentation

See the main [README](../../README.md) for more information.
