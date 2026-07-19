"""Tests for VoicePipeline construction."""

from unittest.mock import patch


class TestVoicePipeline:
    def test_construction_defaults(self):
        with patch("aios.voice.tts.KokoroTTS.__init__", return_value=None), \
             patch("aios.voice.stt.WhisperSTT.__init__", return_value=None), \
             patch("aios.voice.vad.SileroVAD.__init__", return_value=None):
            from aios.voice.pipeline import VoicePipeline
            pipeline = VoicePipeline()
            assert pipeline._sample_rate == 16000

    def test_construction_custom_sample_rate(self):
        with patch("aios.voice.tts.KokoroTTS.__init__", return_value=None), \
             patch("aios.voice.stt.WhisperSTT.__init__", return_value=None), \
             patch("aios.voice.vad.SileroVAD.__init__", return_value=None):
            from aios.voice.pipeline import VoicePipeline
            pipeline = VoicePipeline(sample_rate=44100)
            assert pipeline._sample_rate == 44100

    def test_construction_with_llm_fn(self):
        def my_llm(text):
            return f"Response to: {text}"

        with patch("aios.voice.tts.KokoroTTS.__init__", return_value=None), \
             patch("aios.voice.stt.WhisperSTT.__init__", return_value=None), \
             patch("aios.voice.vad.SileroVAD.__init__", return_value=None):
            from aios.voice.pipeline import VoicePipeline
            pipeline = VoicePipeline(llm_fn=my_llm)
            assert pipeline.llm_fn is my_llm
