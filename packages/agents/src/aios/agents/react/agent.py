"""ReAct agent: Thought → Action → Observation loop.

Extracted and adapted from OpenJarvis NativeReActAgent (Apache 2.0).
Uses AIOS primitives (BaseTool, BaseAgent, EventBus, types).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aios.agents.base import BaseAgent
from aios.agents.events import EventBus, EventType, get_event_bus
from aios.agents.types import (
    Message,
    Role,
    StepType,
    ToolCall,
    ToolResult,
    Trace,
    TraceStep,
)

if TYPE_CHECKING:
    from aios.agents.engine import InferenceEngine
    from aios.agents.tools import BaseTool

REACT_SYSTEM_PROMPT = """\
You are a ReAct agent. For each step, respond with exactly one of:

1. To think and act:
Thought: <your reasoning>
Action: <tool_name>
Action Input: <json arguments>

2. To give a final answer:
Thought: <your reasoning>
Final Answer: <your answer>

{tool_descriptions}"""


@dataclass
class AgentResult:
    """Result of a ReAct agent run."""

    content: str
    tool_results: list[ToolResult] = field(default_factory=list)
    turns: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ReActAgent(BaseAgent):
    """ReAct agent: Thought → Action → Observation loop.

    Wraps an InferenceEngine and a set of tools to perform
    multi-step reasoning with tool use.
    """

    name: str = "react"

    def __init__(
        self,
        engine: InferenceEngine,
        model: str,
        *,
        tools: list[BaseTool] | None = None,
        bus: EventBus | None = None,
        max_turns: int = 10,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> None:
        self._engine = engine
        self._model = model
        self._tools: dict[str, BaseTool] = {t.spec.name: t for t in (tools or [])}
        self._bus = bus or get_event_bus()
        self._max_turns = max_turns
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _build_tool_descriptions(self) -> str:
        """Format tool specs for the system prompt."""
        if not self._tools:
            return "No tools available."
        lines = ["# Available Tools"]
        for tool in self._tools.values():
            spec = tool.spec
            lines.append(f"\n## {spec.name}")
            lines.append(f"Description: {spec.description}")
            if spec.parameters:
                lines.append(f"Parameters: {json.dumps(spec.parameters, indent=2)}")
            if spec.required:
                lines.append(f"Required: {', '.join(spec.required)}")
        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        tool_desc = self._build_tool_descriptions()
        return REACT_SYSTEM_PROMPT.format(tool_descriptions=tool_desc)

    def _parse_response(self, text: str) -> dict[str, str]:
        """Parse ReAct structured output into components."""
        result: dict[str, str] = {
            "thought": "",
            "action": "",
            "action_input": "",
            "final_answer": "",
        }

        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        final_match = re.search(
            r"Final Answer:\s*(.+)", text, re.DOTALL | re.IGNORECASE,
        )
        if final_match:
            result["final_answer"] = final_match.group(1).strip()
            return result

        action_match = re.search(r"Action:\s*(.+)", text, re.IGNORECASE)
        if action_match:
            result["action"] = action_match.group(1).strip()

        input_match = re.search(
            r"Action Input:\s*(.+?)(?=\n\n|\nThought:|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if input_match:
            result["action_input"] = input_match.group(1).strip()

        return result

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call and return the result."""
        tool = self._tools.get(tool_call.name)
        if not tool:
            return ToolResult(
                tool_name=tool_call.name,
                content=f"Tool '{tool_call.name}' not found",
                success=False,
            )
        try:
            args = json.loads(tool_call.arguments) if tool_call.arguments else {}
        except json.JSONDecodeError:
            args = {}
        return await tool.execute(**args)

    async def run(self, query: str, *, trace: Trace | None = None) -> str:
        """Execute the ReAct loop and return the final answer."""
        trace = trace or Trace(query=query, agent=self.name)
        system_prompt = self._build_system_prompt()

        messages: list[Message] = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=query),
        ]

        all_tool_results: list[ToolResult] = []

        self._bus.publish(EventType.AGENT_TURN_START, {
            "agent": self.name,
            "query": query,
        })

        for turn in range(1, self._max_turns + 1):
            t0 = time.monotonic()
            result = await self._engine.complete(
                messages=messages,
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            latency = time.monotonic() - t0

            trace.add_step(TraceStep(
                step_type=StepType.GENERATE,
                timestamp=t0,
                duration_seconds=latency,
                input={"turn": turn, "messages_count": len(messages)},
                output={
                    "content_length": len(result.content),
                    "tokens": result.usage.total_tokens,
                    "model": result.model,
                    "finish_reason": result.finish_reason,
                },
            ))

            # Handle native function calling if provider returned tool_calls
            if result.tool_calls and not result.content:
                for tc in result.tool_calls:
                    self._bus.publish(EventType.TOOL_CALL_START, {
                        "tool": tc.name,
                        "turn": turn,
                    })
                    tool_result = await self._execute_tool(tc)
                    all_tool_results.append(tool_result)
                    self._bus.publish(EventType.TOOL_CALL_END, {
                        "tool": tc.name,
                        "success": tool_result.success,
                        "turn": turn,
                    })
                    trace.add_step(TraceStep(
                        step_type=StepType.TOOL_CALL,
                        timestamp=time.monotonic(),
                        input={"tool": tc.name, "args": tc.arguments},
                        output={
                            "success": tool_result.success,
                            "content": tool_result.content[:200],
                        },
                    ))
                    messages.append(Message(
                        role=Role.TOOL,
                        content=tool_result.content,
                        tool_call_id=tc.id,
                    ))
                continue

            text = result.content
            parsed = self._parse_response(text)

            if parsed["final_answer"]:
                self._bus.publish(EventType.AGENT_TURN_END, {
                    "agent": self.name,
                    "turns": turn,
                    "final": True,
                })
                trace.result = parsed["final_answer"]
                trace.ended_at = time.monotonic()
                return parsed["final_answer"]

            if not parsed["action"]:
                self._bus.publish(EventType.AGENT_TURN_END, {
                    "agent": self.name,
                    "turns": turn,
                    "final": True,
                })
                trace.result = text
                trace.ended_at = time.monotonic()
                return text

            messages.append(Message(role=Role.ASSISTANT, content=text))

            tool_call = ToolCall(
                id=f"react_{turn}",
                name=parsed["action"],
                arguments=parsed["action_input"] or "{}",
            )

            self._bus.publish(EventType.TOOL_CALL_START, {
                "tool": tool_call.name,
                "turn": turn,
            })

            tool_result = await self._execute_tool(tool_call)
            all_tool_results.append(tool_result)

            self._bus.publish(EventType.TOOL_CALL_END, {
                "tool": tool_call.name,
                "success": tool_result.success,
                "turn": turn,
            })

            trace.add_step(TraceStep(
                step_type=StepType.TOOL_CALL,
                timestamp=time.monotonic(),
                input={"tool": tool_call.name, "args": tool_call.arguments},
                output={"success": tool_result.success, "content": tool_result.content[:200]},
            ))

            observation = f"Observation: {tool_result.content}"
            messages.append(Message(role=Role.USER, content=observation))

        self._bus.publish(EventType.AGENT_TURN_END, {
            "agent": self.name,
            "turns": self._max_turns,
            "final": False,
        })
        trace.result = f"Max turns ({self._max_turns}) exceeded"
        trace.ended_at = time.monotonic()
        return f"Max turns ({self._max_turns}) exceeded"

    async def step(self, messages: list[Message], *, trace: Trace | None = None) -> Message:  # noqa: ARG002
        """Execute a single step (one LLM call + optional tool use)."""
        result = await self._engine.complete(
            messages=messages,
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        parsed = self._parse_response(result.content)
        if parsed["final_answer"]:
            return Message(role=Role.ASSISTANT, content=parsed["final_answer"])
        return Message(role=Role.ASSISTANT, content=result.content)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "ReActAgent",
            "engine": type(self._engine).__name__,
            "model": self._model,
            "tools": list(self._tools.keys()),
            "max_turns": self._max_turns,
        }


__all__ = ["REACT_SYSTEM_PROMPT", "AgentResult", "ReActAgent"]
