"""Tests for wake word providers — protocol compliance, implementations, factory."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from aios.voice.wakeword import (
    EnergyFallbackProvider,
    OpenWakeWordProvider,
    WakeWordProvider,
    create_wake_word_provider,
)


def make_audio(silent: bool = False) -> np.ndarray:
    if silent:
        return np.zeros(512, dtype=np.float32)
    return np.ones(512, dtype=np.float32) * 0.5


# --- Protocol compliance ---


class TestWakeWordProtocol:
    def test_is_runtime_checkable(self):
        assert isinstance(EnergyFallbackProvider(), WakeWordProvider)

    def test_has_required_methods(self):
        for method in ("start", "stop", "detect", "is_available", "reset"):
            assert hasattr(WakeWordProvider, method)


# --- OpenWakeWordProvider ---


class TestOpenWakeWordProvider:
    def test_import_failure_returns_unavailable(self):
        with patch.dict("sys.modules", {"openwakeword": None, "openwakeword.model": None}):
            p = OpenWakeWordProvider(wake_phrase="hey ai os")
            assert not p.is_available()
            assert p.detect(make_audio()) is False

    def test_detect_before_start_returns_false(self):
        p = OpenWakeWordProvider.__new__(OpenWakeWordProvider)
        p._model = MagicMock()
        p._available = True
        p._started = False
        p._wake_phrase = "hey ai os"
        assert p.detect(make_audio()) is False

    def test_detect_with_mocked_model_above_threshold(self):
        p = OpenWakeWordProvider.__new__(OpenWakeWordProvider)
        model = MagicMock()
        model.predict.return_value = {"hey_ai_os": 0.85, "other": 0.1}
        p._model = model
        p._available = True
        p._started = True
        p._wake_phrase = "hey ai os"
        assert p.detect(make_audio()) is True

    def test_detect_with_mocked_model_below_threshold(self):
        p = OpenWakeWordProvider.__new__(OpenWakeWordProvider)
        model = MagicMock()
        model.predict.return_value = {"hey_ai_os": 0.3, "other": 0.1}
        p._model = model
        p._available = True
        p._started = True
        p._wake_phrase = "hey ai os"
        assert p.detect(make_audio()) is False

    def test_stop_then_detect_returns_false(self):
        p = OpenWakeWordProvider.__new__(OpenWakeWordProvider)
        p._model = MagicMock()
        p._available = True
        p._wake_phrase = "hey ai os"
        p.start()
        p.stop()
        assert p.detect(make_audio()) is False

    def test_reset_calls_model_reset(self):
        p = OpenWakeWordProvider.__new__(OpenWakeWordProvider)
        model = MagicMock()
        p._model = model
        p._available = True
        p._wake_phrase = "hey ai os"
        p.reset()
        model.reset.assert_called_once()

    def test_reset_handles_model_exception(self):
        p = OpenWakeWordProvider.__new__(OpenWakeWordProvider)
        model = MagicMock()
        model.reset.side_effect = RuntimeError("fail")
        p._model = model
        p._available = True
        p._wake_phrase = "hey ai os"
        p.reset()  # should not raise


# --- EnergyFallbackProvider ---


class TestEnergyFallbackProvider:
    def test_is_always_available(self):
        assert EnergyFallbackProvider().is_available()

    def test_detect_before_start_returns_false(self):
        p = EnergyFallbackProvider(threshold=0.01, min_speech_chunks=1)
        assert p.detect(make_audio()) is False

    def test_detect_energy_above_threshold_triggers(self):
        p = EnergyFallbackProvider(threshold=0.01, min_speech_chunks=1)
        p.start()
        assert p.detect(make_audio()) is True

    def test_detect_silent_audio_returns_false(self):
        p = EnergyFallbackProvider(threshold=0.5, min_speech_chunks=1)
        p.start()
        assert p.detect(make_audio(silent=True)) is False

    def test_consecutive_chunks_required(self):
        p = EnergyFallbackProvider(threshold=0.01, min_speech_chunks=3)
        p.start()
        loud = make_audio()
        assert p.detect(loud) is False
        assert p.detect(loud) is False
        assert p.detect(loud) is True

    def test_cooldown_prevents_repeated_triggers(self):
        p = EnergyFallbackProvider(
            threshold=0.01, min_speech_chunks=1, cooldown_seconds=10.0
        )
        p.start()
        assert p.detect(make_audio()) is True
        # Reset speech count but DON'T call start() (which resets cooldown)
        p._speech_count = 0
        # Should still be in cooldown — last_trigger_time was set moments ago
        assert p.detect(make_audio()) is False

    def test_stop_disables_detection(self):
        p = EnergyFallbackProvider(threshold=0.01, min_speech_chunks=1)
        p.start()
        p.stop()
        assert p.detect(make_audio()) is False

    def test_reset_clears_speech_count(self):
        p = EnergyFallbackProvider(threshold=0.01, min_speech_chunks=3)
        p.start()
        p.detect(make_audio())
        p.reset()
        assert p._speech_count == 0


# --- Factory ---


class TestCreateWakeWordProvider:
    def test_energy_fallback(self):
        p = create_wake_word_provider("energy")
        assert isinstance(p, EnergyFallbackProvider)

    def test_auto_without_openwakeword(self):
        with patch.dict("sys.modules", {"openwakeword": None, "openwakeword.model": None}):
            p = create_wake_word_provider("auto")
            assert isinstance(p, EnergyFallbackProvider)

    def test_unknown_provider_falls_back(self):
        p = create_wake_word_provider("unknown_thing")
        assert isinstance(p, EnergyFallbackProvider)
