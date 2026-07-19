"""Coding Agent — shell execution + code generation.

Inspired by Open Interpreter (MIT) and OpenHands coding patterns.
Generates code, executes it, observes output, and iterates.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from aios.agents.base import BaseAgent
from aios.agents.types import Message, Role, Trace
from aios.tools.builtin import FileSystemTool, ShellExecuteTool

if TYPE_CHECKING:
    from aios.agents.engine import InferenceEngine


_CODING_SYSTEM = """\
You are AIOS Coding Agent — a world-class software engineer.

You can write and execute code to solve problems. When you need to run code:

1. Write the code in a code block:
```python
# your code here
```
or
```bash
# bash command here
```

2. Say EXECUTE to run it.
3. Observe the output and iterate.

You can also:
- Read and write files using the filesystem tool
- Install packages with pip (in the sandbox)
- Debug errors by reading tracebacks
- Explain code clearly

Always write clean, well-commented code. Prefer Python unless bash is more appropriate.
"""

_CODE_BLOCK_RE = re.compile(r"```(python|bash|sh|)\n(.*?)```", re.DOTALL)


class CodingAgent(BaseAgent):
    """Coding agent with code execution capability.

    Architecture (Open Interpreter style):
    1. LLM generates code + explanation
    2. Extract code blocks from response
    3. Execute in sandboxed shell
    4. Feed output back to LLM
    5. Repeat until task complete
    """

    name = "coding"

    def __init__(
        self,
        engine: InferenceEngine,
        model: str = "ollama/codellama",
        *,
        max_iterations: int = 5,
        auto_execute: bool = True,
    ) -> None:
        self._engine = engine
        self._model = model
        self._max_iter = max_iterations
        self._auto_execute = auto_execute
        self._shell = ShellExecuteTool()
        self._fs = FileSystemTool()

    async def run(self, query: str, *, trace: Trace | None = None) -> str:
        """Execute coding task with iterative code generation and execution."""
        conversation: list[Message] = [
            Message(role=Role.SYSTEM, content=_CODING_SYSTEM),
            Message(role=Role.USER, content=query),
        ]

        final_response = ""

        for _iteration in range(self._max_iter):
            result = await self._engine.complete(
                conversation,
                model=self._model,
                max_tokens=4096,
                temperature=0.2,
            )
            response_text = result.content
            final_response = response_text
            conversation.append(Message(role=Role.ASSISTANT, content=response_text))

            # Extract and execute code blocks
            if not self._auto_execute:
                break

            code_blocks = _CODE_BLOCK_RE.findall(response_text)
            if not code_blocks:
                break  # No code to execute — final answer

            execution_outputs = []
            for lang, code in code_blocks:
                lang = lang.strip() or "bash"
                if lang == "python":
                    exec_result = await self._shell.execute(
                        command=code.strip(), language="python", timeout=60
                    )
                else:
                    exec_result = await self._shell.execute(
                        command=code.strip(), language="bash", timeout=60
                    )

                status = "✅" if exec_result.success else "❌"
                execution_outputs.append(
                    f"{status} [{lang}] Exit: {exec_result.metadata.get('exit_code', '?')}\n"
                    f"Output:\n{exec_result.content}"
                )

            # Feed outputs back
            obs_text = "\n\n---\n\n".join(execution_outputs)
            exec_msg = (
                f"Code execution results:\n\n{obs_text}\n\n"
                "Please continue or provide the final answer."
            )
            conversation.append(
                Message(
                    role=Role.USER,
                    content=exec_msg,
                )
            )

        return final_response

    async def step(self, messages: list[Message], *, trace: Trace | None = None) -> Message:
        result = await self._engine.complete(messages, model=self._model, temperature=0.2)
        return Message(role=Role.ASSISTANT, content=result.content)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "CodingAgent",
            "capabilities": ["code_generation", "code_execution", "debugging", "filesystem"],
            "model": self._model,
            "description": (
                "Writes, executes, and debugs code. Powered by Open Interpreter patterns."
            ),
        }


__all__ = ["CodingAgent"]
