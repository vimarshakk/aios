"""Tests for VoiceSession state machine (M8.2).

Tests cover:
- Legal state transitions
- Illegal transition rejection
- Start/stop/interrupt control messages
- Silence timeout behavior
- TTS task lifecycle
- Cleanup and resource management
- Conversation history tracking
- Mode switching (push_to_talk vs always_on)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aios.gateway.main import LEGAL_TRANSITIONS, VoiceMode, VoiceSession, VoiceState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_session(**kwargs) -> VoiceSession:
    """Create a VoiceSession with mocked dependencies."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    vad = MagicMock()
    vad.is_speech = MagicMock(return_value=False)
    vad.reset = MagicMock()
    vad.speech_started = False
    vad.silence_duration = MagicMock(return_value=0.0)
    stt = MagicMock()
    tts = MagicMock()
    return VoiceSession(
        websocket=ws,
        vad=vad,
        stt=stt,
        tts=tts,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# State Machine — Legal Transitions
# ---------------------------------------------------------------------------


class TestLegalTransitions:
    """Verify all legal transitions are defined and work."""

    def test_all_states_have_transitions(self):
        """Every state should have at least one legal transition."""
        all_states = {
            VoiceState.IDLE,
            VoiceState.WAITING_FOR_WAKE,
            VoiceState.LISTENING,
            VoiceState.TRANSCRIBING,
            VoiceState.PLANNING,
            VoiceState.EXECUTING,
            VoiceState.SPEAKING,
        }
        for state in all_states:
            assert state in LEGAL_TRANSITIONS, f"State {state} missing from LEGAL_TRANSITIONS"

    def test_idle_to_listening(self):
        s = make_session()
        assert s.state == VoiceState.IDLE
        assert s.transition(VoiceState.LISTENING)
        assert s.state == VoiceState.LISTENING

    def test_idle_to_waiting_for_wake(self):
        s = make_session()
        assert s.transition(VoiceState.WAITING_FOR_WAKE)
        assert s.state == VoiceState.WAITING_FOR_WAKE

    def test_listening_to_transcribing(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        assert s.transition(VoiceState.TRANSCRIBING)
        assert s.state == VoiceState.TRANSCRIBING

    def test_listening_to_idle(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        assert s.transition(VoiceState.IDLE)
        assert s.state == VoiceState.IDLE

    def test_transcribing_to_planning(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        assert s.transition(VoiceState.PLANNING)
        assert s.state == VoiceState.PLANNING

    def test_planning_to_executing(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        assert s.transition(VoiceState.EXECUTING)
        assert s.state == VoiceState.EXECUTING

    def test_executing_to_speaking(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        assert s.transition(VoiceState.SPEAKING)
        assert s.state == VoiceState.SPEAKING

    def test_speaking_to_listening(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        assert s.transition(VoiceState.LISTENING)
        assert s.state == VoiceState.LISTENING

    def test_speaking_to_idle(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        assert s.transition(VoiceState.IDLE)
        assert s.state == VoiceState.IDLE


# ---------------------------------------------------------------------------
# State Machine — Illegal Transitions
# ---------------------------------------------------------------------------


class TestIllegalTransitions:
    """Verify illegal transitions are rejected."""

    def test_idle_to_speaking(self):
        s = make_session()
        assert not s.transition(VoiceState.SPEAKING)
        assert s.state == VoiceState.IDLE  # unchanged

    def test_idle_to_transcribing(self):
        s = make_session()
        assert not s.transition(VoiceState.TRANSCRIBING)
        assert s.state == VoiceState.IDLE

    def test_listening_to_speaking(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        assert not s.transition(VoiceState.SPEAKING)
        assert s.state == VoiceState.LISTENING

    def test_transcribing_to_speaking(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        assert not s.transition(VoiceState.SPEAKING)
        assert s.state == VoiceState.TRANSCRIBING

    def test_planning_to_listening(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        assert not s.transition(VoiceState.LISTENING)
        assert s.state == VoiceState.PLANNING

    def test_speaking_to_planning(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        assert not s.transition(VoiceState.PLANNING)
        assert s.state == VoiceState.SPEAKING


# ---------------------------------------------------------------------------
# Control Messages — Start
# ---------------------------------------------------------------------------


class TestStartControl:
    """Test start control message handling."""

    @pytest.mark.asyncio
    async def test_start_transitions_to_listening(self):
        s = make_session()
        await s.handle_start({"type": "start", "mode": "push_to_talk"})
        assert s.state == VoiceState.LISTENING

    @pytest.mark.asyncio
    async def test_start_sends_listening_event(self):
        s = make_session()
        await s.handle_start({"type": "start", "mode": "always_on"})
        calls = [c.args[0] for c in s._ws.send_json.call_args_list]
        listening_events = [c for c in calls if c.get("type") == "listening"]
        assert len(listening_events) == 1
        assert listening_events[0]["mode"] == "always_on"

    @pytest.mark.asyncio
    async def test_start_sets_mode(self):
        s = make_session()
        await s.handle_start({"type": "start", "mode": "always_on"})
        assert s.mode == "always_on"

    @pytest.mark.asyncio
    async def test_start_sets_agent(self):
        s = make_session()
        await s.handle_start({"type": "start", "agent": "research"})
        assert s._agent_name == "research"

    @pytest.mark.asyncio
    async def test_start_resets_buffer(self):
        s = make_session()
        s._audio_buffer.extend(b"fake data")
        await s.handle_start({"type": "start"})
        assert len(s._audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_start_when_not_idle_sends_error(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        await s.handle_start({"type": "start"})
        calls = [c.args[0] for c in s._ws.send_json.call_args_list]
        error_events = [c for c in calls if c.get("type") == "error"]
        assert len(error_events) == 1


# ---------------------------------------------------------------------------
# Control Messages — Stop
# ---------------------------------------------------------------------------


class TestStopControl:
    """Test stop control message handling."""

    @pytest.mark.asyncio
    async def test_stop_transitions_to_idle(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        await s.handle_stop()
        assert s.state == VoiceState.IDLE

    @pytest.mark.asyncio
    async def test_stop_sends_stopped_event(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        await s.handle_stop()
        calls = [c.args[0] for c in s._ws.send_json.call_args_list]
        stopped_events = [c for c in calls if c.get("type") == "stopped"]
        assert len(stopped_events) == 1

    @pytest.mark.asyncio
    async def test_stop_resets_buffer(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s._audio_buffer.extend(b"fake data")
        await s.handle_stop()
        assert len(s._audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_stop_cancels_tts(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel.return_value = True
        s._tts_task = mock_task
        await s.handle_stop()
        mock_task.cancel.assert_called_once()


# ---------------------------------------------------------------------------
# Control Messages — Interrupt
# ---------------------------------------------------------------------------


class TestInterruptControl:
    """Test interrupt (barge-in) handling."""

    @pytest.mark.asyncio
    async def test_interrupt_cancels_tts(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel.return_value = True
        s._tts_task = mock_task
        await s.handle_interrupt()
        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_interrupt_from_speaking_goes_to_listening(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        await s.handle_interrupt()
        assert s.state == VoiceState.LISTENING

    @pytest.mark.asyncio
    async def test_interrupt_sends_interrupted_event(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        await s.handle_interrupt()
        calls = [c.args[0] for c in s._ws.send_json.call_args_list]
        interrupted = [c for c in calls if c.get("type") == "interrupted"]
        assert len(interrupted) == 1

    @pytest.mark.asyncio
    async def test_interrupt_resets_buffer(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        s.transition(VoiceState.EXECUTING)
        s.transition(VoiceState.SPEAKING)
        s._audio_buffer.extend(b"fake data")
        await s.handle_interrupt()
        assert len(s._audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_interrupt_from_planning_goes_to_idle(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        s.transition(VoiceState.TRANSCRIBING)
        s.transition(VoiceState.PLANNING)
        await s.handle_interrupt()
        assert s.state == VoiceState.IDLE


# ---------------------------------------------------------------------------
# Conversation History
# ---------------------------------------------------------------------------


class TestConversationHistory:
    """Test conversation history tracking."""

    def test_history_starts_empty(self):
        s = make_session()
        assert s.conversation_history == []

    def test_history_is_mutable(self):
        s = make_session()
        s._conversation_history.append({"role": "user", "content": "hello"})
        assert len(s.conversation_history) == 1
        assert s.conversation_history[0]["content"] == "hello"


# ---------------------------------------------------------------------------
# Session Properties
# ---------------------------------------------------------------------------


class TestSessionProperties:
    """Test session metadata."""

    def test_default_session_id(self):
        s = make_session()
        assert s.session_id.startswith("voice_")
        assert len(s.session_id) == 14  # "voice_" + 8 hex

    def test_custom_session_id(self):
        s = make_session(session_id="custom_123")
        assert s.session_id == "custom_123"

    def test_default_mode(self):
        s = make_session()
        assert s.mode == VoiceMode.PUSH_TO_TALK

    def test_custom_mode(self):
        s = make_session(mode="always_on")
        assert s.mode == "always_on"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    """Test resource cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_cancels_tts(self):
        s = make_session()
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel.return_value = True
        s._tts_task = mock_task
        await s.cleanup()
        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_cancels_silence(self):
        s = make_session()
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel.return_value = True
        s._silence_task = mock_task
        await s.cleanup()
        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_resets_vad(self):
        s = make_session()
        await s.cleanup()
        s._vad.reset.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_clears_buffer(self):
        s = make_session()
        s._audio_buffer.extend(b"data")
        await s.cleanup()
        assert len(s._audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_cleanup_marks_closed(self):
        s = make_session()
        assert not s._closed
        await s.cleanup()
        assert s._closed

    @pytest.mark.asyncio
    async def test_send_after_cleanup_is_noop(self):
        s = make_session()
        await s.cleanup()
        await s.send({"type": "test"})
        # Should not raise, just silently drop
        s._ws.send_json.assert_not_called()


# ---------------------------------------------------------------------------
# Send Method
# ---------------------------------------------------------------------------


class TestSendMethod:
    """Test event sending."""

    @pytest.mark.asyncio
    async def test_send_json_to_websocket(self):
        s = make_session()
        await s.send({"type": "test", "value": 42})
        s._ws.send_json.assert_called_once_with({"type": "test", "value": 42})

    @pytest.mark.asyncio
    async def test_send_after_close_silently_drops(self):
        s = make_session()
        s._closed = True
        await s.send({"type": "test"})
        s._ws.send_json.assert_not_called()


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_double_transition_same_state_rejected(self):
        s = make_session()
        s.transition(VoiceState.LISTENING)
        assert not s.transition(VoiceState.LISTENING)  # can't go to same state

    def test_full_lifecycle(self):
        """Test the complete voice lifecycle: idle → listen → transcribe → plan → execute → speak → listen."""
        s = make_session()
        assert s.state == VoiceState.IDLE

        s.transition(VoiceState.LISTENING)
        assert s.state == VoiceState.LISTENING

        s.transition(VoiceState.TRANSCRIBING)
        assert s.state == VoiceState.TRANSCRIBING

        s.transition(VoiceState.PLANNING)
        assert s.state == VoiceState.PLANNING

        s.transition(VoiceState.EXECUTING)
        assert s.state == VoiceState.EXECUTING

        s.transition(VoiceState.SPEAKING)
        assert s.state == VoiceState.SPEAKING

        s.transition(VoiceState.LISTENING)
        assert s.state == VoiceState.LISTENING

        s.transition(VoiceState.IDLE)
        assert s.state == VoiceState.IDLE
