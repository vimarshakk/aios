"""Speech-to-text using Faster-Whisper (CTranslate2 optimized)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


class WhisperSTT:
    """Fast local STT using faster-whisper."""

    def __init__(
        self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8",
    ) -> None:
        from faster_whisper import WhisperModel
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio: np.ndarray, *, language: str | None = None) -> str:
        """Transcribe audio numpy array to text."""
        segments, _info = self._model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        return "".join(seg.text for seg in segments)


__all__ = ["WhisperSTT"]
