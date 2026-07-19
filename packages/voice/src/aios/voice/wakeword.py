"""Wake word detection with pluggable providers.

Provides an abstract WakeWordProvider interface and two implementations:
- OpenWakeWordProvider: Uses openwakeword library (optional dependency)
- EnergyFallbackProvider: Simple energy-based heuristic (always available)

Usage:
    provider = EnergyFallbackProvider()
    provider.start()
    while True:
        if provider.detect(audio_chunk):
            print("Wake word detected!")
    provider.stop()
"""

from __future__ import annotations

import logging
import time
from typing import Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 512  # 32ms at 16kHz


@runtime_checkable
class WakeWordProvider(Protocol):
    """Interface for wake word detection providers."""

    def start(self) -> None:
        """Start the wake word detector."""
        ...

    def stop(self) -> None:
        """Stop the wake word detector."""
        ...

    def is_available(self) -> bool:
        """Check if the provider is available and ready."""
        ...

    def detect(self, audio: np.ndarray) -> bool:
        """Check if audio chunk contains the wake word."""
        ...

    def reset(self) -> None:
        """Reset detection state between utterances."""
        ...


class OpenWakeWordProvider:
    """Wake word detection using openwakeword library.

    Requires: pip install openwakeword
    Falls back gracefully if not installed.
    """

    def __init__(self, wake_phrase: str = "hey ai os") -> None:
        self._wake_phrase = wake_phrase
        self._model = None
        self._started = False
        self._available = False

        try:
            from openwakeword.model import Model as OwwModel
            self._model = OwwModel(wakeword_models=[wake_phrase])
            self._available = True
            logger.info("OpenWakeWord provider initialized with phrase: %s", wake_phrase)
        except ImportError:
            logger.info(
                "openwakeword not installed. Use: pip install openwakeword. "
                "Falling back to EnergyFallbackProvider."
            )
        except Exception as e:
            logger.warning("Failed to initialize openwakeword: %s", e)

    def start(self) -> None:
        """Start detection."""
        self._started = True

    def stop(self) -> None:
        """Stop detection."""
        self._started = False

    def is_available(self) -> bool:
        """Check if openwakeword is installed and initialized."""
        return self._available and self._model is not None

    def detect(self, audio: np.ndarray) -> bool:
        """Run wake word detection on an audio chunk.

        Args:
            audio: Float32 PCM audio chunk (mono, 16kHz).

        Returns:
            True if wake word detected.
        """
        if not self.is_available() or not self._started:
            return False

        try:
            prediction = self._model.predict(audio)
            # openwakeword returns dict of {model_name: score}
            for _name, score in prediction.items():
                if score > 0.5:
                    logger.debug("Wake word detected (score=%.2f)", score)
                    return True
        except Exception as e:
            logger.debug("Wake word detection error: %s", e)

        return False

    def reset(self) -> None:
        """Reset model state."""
        if self._model is not None:
            try:
                self._model.reset()
            except Exception:
                pass


class EnergyFallbackProvider:
    """Simple energy-based wake word heuristic.

    Detects sustained energy above a threshold as a proxy for speech.
    This is a low-CPU fallback when openwakeword is not available.

    Detection logic:
    - Track energy over a sliding window
    - When energy exceeds threshold for consecutive chunks, trigger detection
    - Cooldown period prevents repeated triggers
    """

    def __init__(
        self,
        threshold: float = 0.02,
        min_speech_chunks: int = 5,
        cooldown_seconds: float = 2.0,
    ) -> None:
        self._threshold = threshold
        self._min_speech_chunks = min_speech_chunks
        self._cooldown_seconds = cooldown_seconds
        self._speech_count = 0
        self._last_trigger_time: float | None = None
        self._started = False

    def start(self) -> None:
        """Start detection."""
        self._started = True
        self._speech_count = 0
        self._last_trigger_time = None

    def stop(self) -> None:
        """Stop detection."""
        self._started = False

    def is_available(self) -> bool:
        """Always available — no external dependencies."""
        return True

    def detect(self, audio: np.ndarray) -> bool:
        """Check if audio energy suggests speech/wake word.

        Args:
            audio: Float32 PCM audio chunk (mono, 16kHz).

        Returns:
            True if energy pattern suggests wake word.
        """
        if not self._started:
            return False

        # Calculate RMS energy
        energy = float(np.sqrt(np.mean(audio ** 2)))

        if energy >= self._threshold:
            self._speech_count += 1
        else:
            self._speech_count = max(0, self._speech_count - 1)

        # Check if we have enough consecutive speech chunks
        if self._speech_count >= self._min_speech_chunks:
            # Check cooldown
            now = time.monotonic()
            if self._last_trigger_time is None or (
                now - self._last_trigger_time > self._cooldown_seconds
            ):
                self._last_trigger_time = now
                self._speech_count = 0
                logger.debug("Energy-based wake detected (energy=%.4f)", energy)
                return True

        return False

    def reset(self) -> None:
        """Reset detection state."""
        self._speech_count = 0


def create_wake_word_provider(
    provider: str = "auto",
    wake_phrase: str = "hey ai os",
    **kwargs,
) -> WakeWordProvider:
    """Factory function to create a wake word provider.

    Args:
        provider: "openwakeword", "energy", or "auto" (try openwakeword, fallback to energy)
        wake_phrase: Wake phrase for openwakeword provider
        **kwargs: Additional arguments for the provider

    Returns:
        A WakeWordProvider instance.
    """
    if provider == "openwakeword":
        return OpenWakeWordProvider(wake_phrase=wake_phrase)
    elif provider == "energy":
        return EnergyFallbackProvider(**kwargs)
    else:  # auto
        oww = OpenWakeWordProvider(wake_phrase=wake_phrase)
        if oww.is_available():
            return oww
        return EnergyFallbackProvider(**kwargs)


__all__ = [
    "WakeWordProvider",
    "OpenWakeWordProvider",
    "EnergyFallbackProvider",
    "create_wake_word_provider",
]
