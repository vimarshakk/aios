# AIOS Memory Package

The memory package provides persistent and ephemeral memory storage for AIOS.

## Features

- **Persistent Memory** - Long-term storage with vector search
- **Ephemeral Memory** - Short-term session-based memory
- **Vector Search** - Semantic search across stored memories
- **Summarization** - Automatic memory summarization
- **Metadata** - Rich metadata for memory categorization

## Quick Start

```python
from aios.memory import Memory

memory = Memory()

# Store a memory
await memory.store(
    "user_preference",
    "I prefer dark mode in all applications",
    metadata={"category": "ui"}
)

# Search for relevant memories
results = await memory.search("What are the user's UI preferences?")
print(results)
```

## Memory Types

### Persistent Memory
Long-term storage that survives across sessions:

```python
await memory.store_persistent(
    "fact",
    "The user's name is Alice",
    importance=0.9
)
```

### Ephemeral Memory
Short-term storage for current session:

```python
await memory.store_ephemeral(
    "context",
    "Currently discussing Python async patterns"
)
```

## Vector Search

```python
# Semantic search
results = await memory.search(
    "Python concurrency",
    limit=5,
    threshold=0.7
)

# Filter by metadata
results = await memory.search(
    "preferences",
    filters={"category": "ui"}
)
```

## Documentation

See the main [README](../../README.md) for more information.
