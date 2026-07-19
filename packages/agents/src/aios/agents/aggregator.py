"""Result aggregation — combine multi-agent subtask results into a final response."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aios.agents.multi_executor import SubtaskResult


class ResultAggregator:
    """Aggregates subtask results into a single response.

    M1 strategy: sequential concatenation with headers and status markers.
    Future: LLM-powered synthesis for coherent multi-agent responses.
    """

    def aggregate(
        self,
        results: list[SubtaskResult],
        query: str,  # noqa: ARG002
    ) -> str:
        """Combine subtask results into a final response string.

        Format:
        - Single successful result: return response directly
        - Multiple results: concatenate with headers
        - Failed results: include error markers
        """
        if not results:
            return "No results from multi-agent execution."

        if len(results) == 1:
            r = results[0]
            if r.success:
                return r.response
            return f"Agent '{r.agent_name}' failed: {r.error}"

        succeeded = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        parts = []
        for i, r in enumerate(succeeded, 1):
            header = f"Result {i} (from {r.agent_name})"
            parts.append(f"{header}\n{'─' * len(header)}\n{r.response}")
        parts.extend(
            f"⚠ Agent '{r.agent_name}' failed: {r.error}" for r in failed
        )

        return "\n\n".join(parts)

    def aggregate_structured(
        self,
        results: list[SubtaskResult],
        query: str,
    ) -> dict[str, Any]:
        """Return a structured aggregation for programmatic consumption."""
        succeeded = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        return {
            "query": query,
            "total_subtasks": len(results),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "results": [
                {
                    "subtask_id": r.subtask_id,
                    "agent": r.agent_name,
                    "response": r.response,
                    "duration_ms": r.duration_ms,
                }
                for r in succeeded
            ],
            "errors": [
                {
                    "subtask_id": r.subtask_id,
                    "agent": r.agent_name,
                    "error": r.error,
                }
                for r in failed
            ],
            "total_duration_ms": sum(r.duration_ms for r in results),
        }
