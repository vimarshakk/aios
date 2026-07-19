"""Full voice pipeline: microphone → VAD → STT → LLM → TTS → speaker.

Extracted from OpenJarvis voice patterns (Apache 2.0).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aios.voice.stt import WhisperSTT
from aios.voice.tts import KokoroTTS
from aios.voice.vad import SileroVAD

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy as np


class VoicePipeline:
    """End-to-end voice interaction pipeline."""

    def __init__(
        self,
        *,
        stt: WhisperSTT | None = None,
        tts: KokoroTTS | None = None,
        vad: SileroVAD | None = None,
        llm_fn: Callable[[str], str] | None = None,
        sample_rate: int = 16000,
    ) -> None:
        self.stt = stt or WhisperSTT()
        self.tts = tts or KokoroTTS()
        self.vad = vad or SileroVAD(sample_rate=sample_rate)
        self.llm_fn = llm_fn
        self._sample_rate = sample_rate

    async def process_audio(self, audio: np.ndarray) -> str:
        """Process a chunk of audio: VAD → STT → LLM → TTS text."""
        if not self.vad.is_speech(audio):
            return ""
        text = self.stt.transcribe(audio)
        if not text.strip():
            return ""
        if self.llm_fn and callable(self.llm_fn):
            import asyncio
            if asyncio.iscoroutinefunction(self.llm_fn):
                response = await self.llm_fn(text)
            else:
                response = self.llm_fn(text)
            return response
        return text

    def text_to_audio(self, text: str) -> np.ndarray:
        """Convert text response to audio for playback."""
        return self.tts.synthesize(text)


__all__ = ["VoicePipeline"]
