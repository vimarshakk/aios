"""E2E smoke tests for VoiceSession.

Tests the VoiceSession class directly with a fake WebSocket:
1. Send ready event → verify session_id
2. handle_start → verify transitions to LISTENING
3. handle_stop → verify transitions to IDLE
4. handle_interrupt → verify correct transition
5. handle_configure → verify wake word state
6. Full lifecycle: create → start → audio → stop → cleanup
7. Audio ignored when not listening
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from aios.gateway.main import VoiceSession, VoiceState


def make_pcm_chunk(duration_ms: int = 100, silent: bool = False) -> bytes:
    samples = int(16000 * duration_ms / 1000)
    if silent:
        audio = np.zeros(samples, dtype=np.float32)
    else:
        audio = np.random.randn(samples).astype(np.float32) * 0.5
    return audio.tobytes()


class FakeWebSocket:
    def __init__(self):
        self.sent: list[str] = []

    async def send_json(self, data: dict) -> None:
        self.sent.append(json.dumps(data))

    async def close(self) -> None:
        pass


def parse_events(ws: FakeWebSocket) -> list[dict]:
    return [json.loads(msg) for msg in ws.sent]


def get_events_by_type(events: list[dict], event_type: str) -> list[dict]:
    return [e for e in events if e.get("type") == event_type]


def make_session(**kwargs) -> tuple[VoiceSession, FakeWebSocket]:
    ws = FakeWebSocket()
    vad = MagicMock()
    vad.is_speech.return_value = False
    vad.speech_started = False
    vad.reset = MagicMock()
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value="Hello")
    tts = MagicMock()
    tts.synthesize = AsyncMock(return_value=b"\x00" * 100)
    session = VoiceSession(ws, vad, stt, tts, **kwargs)
    return session, ws


class TestVoiceSessionE2E:
    @pytest.mark.asyncio
    async def test_ready_event_sent_in_endpoint(self):
        """The 'ready' event is sent by the ws_voice endpoint, not the session.
        Test that the session has a session_id set."""
        session, ws = make_session()
        assert session.session_id is not None
        assert len(session.session_id) > 0
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_start_transitions_to_listening(self):
        session, ws = make_session()
        ws.sent.clear()
        await session.handle_start({"type": "start", "mode": "push_to_talk"})
        assert session.state == VoiceState.LISTENING
        events = parse_events(ws)
        listening = get_events_by_type(events, "listening")
        assert len(listening) == 1
        assert listening[0]["mode"] == "push_to_talk"
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_stop_transitions_to_idle(self):
        session, ws = make_session()
        await session.handle_start({"type": "start"})
        ws.sent.clear()
        await session.handle_stop()
        assert session.state == VoiceState.IDLE
        events = parse_events(ws)
        stopped = get_events_by_type(events, "stopped")
        assert len(stopped) == 1
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_interrupt_from_speaking_goes_to_listening(self):
        session, ws = make_session()
        session._state = VoiceState.SPEAKING
        ws.sent.clear()
        await session.handle_interrupt()
        assert session.state == VoiceState.LISTENING
        events = parse_events(ws)
        interrupted = get_events_by_type(events, "interrupted")
        assert len(interrupted) == 1
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_interrupt_from_planning_goes_to_idle(self):
        session, ws = make_session()
        session._state = VoiceState.PLANNING
        ws.sent.clear()
        await session.handle_interrupt()
        assert session.state == VoiceState.IDLE
        events = parse_events(ws)
        interrupted = get_events_by_type(events, "interrupted")
        assert len(interrupted) == 1
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_configure_wake_word_transitions_to_waiting(self):
        session, ws = make_session()
        ws.sent.clear()
        await session.handle_configure({
            "type": "configure",
            "wake_word": {"enabled": True, "phrase": "hey ai os"},
        })
        assert session.state == VoiceState.WAITING_FOR_WAKE
        events = parse_events(ws)
        wake_configured = get_events_by_type(events, "wake_configured")
        assert len(wake_configured) == 1
        assert wake_configured[0]["phrase"] == "hey ai os"
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        session, ws = make_session()
        assert session.state == VoiceState.IDLE
        await session.handle_start({"type": "start"})
        assert session.state == VoiceState.LISTENING
        await session.handle_stop()
        assert session.state == VoiceState.IDLE
        await session.cleanup()
        events = parse_events(ws)
        types = [e["type"] for e in events]
        assert "listening" in types
        assert "stopped" in types

    @pytest.mark.asyncio
    async def test_audio_buffer_accumulates(self):
        session, ws = make_session()
        vad = session._vad
        vad.is_speech.return_value = True  # Mock speech detection
        vad.speech_started = True
        vad.silence_duration.return_value = 0.0  # Not silent yet
        await session.handle_start({"type": "start"})
        chunk = make_pcm_chunk(100)
        await session.handle_audio(chunk)
        await session.handle_audio(chunk)
        assert len(session._audio_buffer) > 0
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_audio_ignored_when_not_listening(self):
        session, ws = make_session()
        await session.handle_audio(make_pcm_chunk(100))
        assert len(session._audio_buffer) == 0
        await session.cleanup()
