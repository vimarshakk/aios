"""Text-to-speech using Kokoro ONNX (local, fast, high-quality)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


class KokoroTTS:
    """Fast local TTS using Kokoro ONNX model."""

    def __init__(self, model_path: str = "kokoro-v0_19.onnx", voice: str = "af_heart") -> None:
        from kokoro_onnx import Kokoro
        self._kokoro = Kokoro(model_path)
        self._voice = voice

    def synthesize(self, text: str, *, speed: float = 1.0) -> np.ndarray:
        """Synthesize text to audio numpy array (24kHz)."""
        audio, _sample_rate = self._kokoro.create(
            text,
            voice=self._voice,
            speed=speed,
        )
        return audio

    def list_voices(self) -> list[str]:
        """List available voice presets."""
        return ["af_heart", "af_sarah", "am_adam", "bf_emma", "bm_george"]


__all__ = ["KokoroTTS"]
