"""Voice Activity Detection using Silero VAD."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


class SileroVAD:
    """Detect speech segments in audio using Silero VAD."""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000) -> None:
        import torch
        model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        self._model = model
        self._threshold = threshold
        self._sample_rate = sample_rate

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Check if an audio chunk contains speech."""
        import torch
        tensor = torch.from_numpy(audio_chunk).float()
        if tensor.dim() == 1:
            tensor = tensor.unsqueeze(0)
        score = self._model(tensor, self._sample_rate).item()
        return score >= self._threshold

    def reset(self) -> None:
        """Reset VAD state between utterances."""
        self._model.reset_states()


__all__ = ["SileroVAD"]
