"use client";

import { useCallback, useRef, useState } from "react";

interface VoiceState {
  listening: boolean;
  speaking: boolean;
  transcript: string;
  supported: boolean;
}

interface UseVoiceOptions {
  onTranscript?: (text: string) => void;
  lang?: string;
}

export function useVoice({ onTranscript, lang = "en-US" }: UseVoiceOptions = {}) {
  const [state, setState] = useState<VoiceState>({
    listening: false,
    speaking: false,
    transcript: "",
    supported:
      typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window),
  });

  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // -------------------------------------------------------------------------
  // STT — Web Speech API SpeechRecognition
  // -------------------------------------------------------------------------

  const startListening = useCallback(() => {
    const SpeechRecognition =
      (window as Window & { SpeechRecognition?: typeof window.SpeechRecognition; webkitSpeechRecognition?: typeof window.SpeechRecognition }).SpeechRecognition ||
      (window as Window & { SpeechRecognition?: typeof window.SpeechRecognition; webkitSpeechRecognition?: typeof window.SpeechRecognition }).webkitSpeechRecognition;

    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setState((s) => ({ ...s, listening: true, transcript: "" }));
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }
      const current = final || interim;
      setState((s) => ({ ...s, transcript: current }));
      if (final && onTranscript) {
        onTranscript(final.trim());
      }
    };

    recognition.onend = () => {
      setState((s) => ({ ...s, listening: false }));
    };

    recognition.onerror = () => {
      setState((s) => ({ ...s, listening: false }));
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [lang, onTranscript]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setState((s) => ({ ...s, listening: false }));
  }, []);

  // -------------------------------------------------------------------------
  // TTS — Browser SpeechSynthesis (works everywhere, no download)
  // -------------------------------------------------------------------------

  const speak = useCallback((text: string, voiceName?: string) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Try to find a good voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find((v) =>
      voiceName ? v.name.includes(voiceName) : v.name.includes("Samantha") || v.name.includes("Alex") || v.lang === "en-US"
    );
    if (preferred) utterance.voice = preferred;

    utterance.onstart = () => setState((s) => ({ ...s, speaking: true }));
    utterance.onend = () => setState((s) => ({ ...s, speaking: false }));
    utterance.onerror = () => setState((s) => ({ ...s, speaking: false }));

    window.speechSynthesis.speak(utterance);
  }, []);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel();
    setState((s) => ({ ...s, speaking: false }));
  }, []);

  return {
    ...state,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  };
}
