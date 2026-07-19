"""AIOS Search Service — semantic and full-text search."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("aios.search")


class SearchService:
    """Lightweight search service for querying memories, goals, and content.

    Provides both keyword and semantic search over stored data.
    """

    def __init__(self) -> None:
        self._ready = False

    async def initialize(self) -> None:
        """Initialize search indices."""
        self._ready = True
        logger.info("Search service initialized")

    async def search(
        self,
        query: str,
        *,
        user_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search across all indexed content.

        Args:
            query: Search query string.
            user_id: Optional user scope.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            List of search result dicts.
        """
        # Placeholder — returns empty until vector/FTS backend is wired
        return []

    async def index(self, content: str, metadata: dict[str, Any]) -> None:
        """Index a document for search.

        Args:
            content: Text content to index.
            metadata: Associated metadata (user_id, type, etc).
        """
        logger.debug("Index: %s (metadata=%s)", content[:80], list(metadata.keys()))

    async def close(self) -> None:
        """Shut down the search service."""
        self._ready = False
        logger.info("Search service closed")


_service: SearchService | None = None


def get_search_service() -> SearchService:
    """Get the global search service singleton."""
    global _service
    if _service is None:
        _service = SearchService()
    return _service
