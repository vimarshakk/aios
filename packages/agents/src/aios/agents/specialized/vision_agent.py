"""Vision Agent — screenshot analysis and image understanding."""

from __future__ import annotations

import base64
import pathlib
from typing import TYPE_CHECKING, Any

from aios.agents.base import BaseAgent
from aios.agents.types import Message, Role, Trace
from aios.tools.builtin import ScreenshotTool

if TYPE_CHECKING:
    from aios.agents.engine import InferenceEngine


_VISION_SYSTEM = """\
You are AIOS Vision Agent — an expert at analyzing images, screenshots, and visual content.

You can:
- Analyze screenshots of the user's screen
- Describe what you see in images
- Extract text from images (OCR)
- Answer questions about visual content
- Identify UI elements, charts, diagrams
- Read documents and PDFs visually

Provide detailed, accurate descriptions of visual content.
"""


class VisionAgent(BaseAgent):
    """Vision agent for image analysis and screenshot understanding.

    Uses multimodal LLMs (Gemini Vision, GPT-4V, LLaVA) to analyze images.
    Falls back to text description when vision model unavailable.
    """

    name = "vision"

    def __init__(
        self,
        engine: InferenceEngine,
        model: str = "ollama/llava",
        *,
        vision_model: str | None = None,
    ) -> None:
        self._engine = engine
        self._model = model
        self._vision_model = vision_model or model
        self._screenshot = ScreenshotTool()

    async def analyze_image(
        self, image_path: str | pathlib.Path, question: str = "Describe this image in detail."
    ) -> str:
        """Analyze an image file using vision model."""
        path = pathlib.Path(image_path)
        if not path.exists():
            return f"Image not found: {image_path}"

        # Try to load image as base64 for vision-capable models
        try:
            image_data = path.read_bytes()
            b64_image = base64.b64encode(image_data).decode()
            ext = path.suffix.lower().lstrip(".")
            mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "gif", "webp") else "image/png"

            # Vision-capable message format
            messages = [
                Message(role=Role.SYSTEM, content=_VISION_SYSTEM),
                Message(
                    role=Role.USER,
                    content=f"data:{mime};base64,{b64_image}\n\n{question}",
                ),
            ]
            result = await self._engine.complete(
                messages, model=self._vision_model, max_tokens=2048
            )
            return result.content
        except Exception as e:
            return (
                f"Vision analysis failed: {e}. "
                "Ensure you're using a vision-capable model "
                "(llava, gemini, gpt-4o)."
            )

    async def analyze_screen(self, question: str = "What do you see on the screen?") -> str:
        """Take a screenshot and analyze it."""
        # Capture screenshot
        screenshot_result = await self._screenshot.execute(filename="vision_capture.png")
        if not screenshot_result.success:
            return f"Screenshot failed: {screenshot_result.content}"

        screenshot_path = screenshot_result.metadata.get("path", "")
        return await self.analyze_image(screenshot_path, question)

    async def run(self, query: str, *, trace: Trace | None = None) -> str:
        """Process a vision task."""
        q_lower = query.lower()

        # Check if asking about screen
        if any(
            w in q_lower
            for w in ("screen", "screenshot", "what do you see", "my screen", "display")
        ):
            return await self.analyze_screen(query)

        # Check if image path is mentioned
        import re

        path_match = re.search(
            r"['\"]?(/[\w/.-]+\.(png|jpg|jpeg|gif|webp|pdf))['\"]?", query, re.IGNORECASE
        )
        if path_match:
            image_path = path_match.group(1)
            return await self.analyze_image(image_path, query)

        # Fallback: general vision question with LLM
        messages = [
            Message(role=Role.SYSTEM, content=_VISION_SYSTEM),
            Message(role=Role.USER, content=query),
        ]
        result = await self._engine.complete(messages, model=self._model, max_tokens=1024)
        return result.content

    async def step(self, messages: list[Message], *, trace: Trace | None = None) -> Message:
        result = await self._engine.complete(messages, model=self._model)
        return Message(role=Role.ASSISTANT, content=result.content)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "VisionAgent",
            "capabilities": ["screenshot_analysis", "image_description", "ocr", "visual_qa"],
            "model": self._vision_model,
            "description": (
                "Analyzes images, screenshots, and visual content using vision-capable models."
            ),
        }


__all__ = ["VisionAgent"]
