"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { VoiceClient, type VoiceEvent, type VoiceMode } from "@/lib/voice-client";

export type VoiceState =
  | "idle"
  | "waiting_for_wake"
  | "listening"
  | "transcribing"
  | "planning"
  | "executing"
  | "speaking";

interface UseVoiceStreamOptions {
  agent?: string;
  model?: string;
  autoConnect?: boolean;
  onTranscript?: (text: string) => void;
  onResponse?: (text: string) => void;
}

const ALWAYS_ON_KEY = "aios_voice_always_on";

export function useVoiceStream(options: UseVoiceStreamOptions = {}) {
  const clientRef = useRef<VoiceClient | null>(null);
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<VoiceState>("idle");
  const [mode, setMode] = useState<VoiceMode>("push_to_talk");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [speechLevel, setSpeechLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [alwaysOn, setAlwaysOn] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(ALWAYS_ON_KEY) === "true";
  });

  const onTranscriptRef = useRef(options.onTranscript);
  const onResponseRef = useRef(options.onResponse);
  onTranscriptRef.current = options.onTranscript;
  onResponseRef.current = options.onResponse;

  // Persist always-on preference
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(ALWAYS_ON_KEY, String(alwaysOn));
    }
  }, [alwaysOn]);

  const handleEvent = useCallback((event: VoiceEvent) => {
    switch (event.type) {
      case "ready":
        setConnected(true);
        setError(null);
        break;
      case "listening":
        setState("listening");
        setMode(event.mode as VoiceMode || "push_to_talk");
        break;
      case "stopped":
        setState("idle");
        break;
      case "silence_timeout":
        setState("idle");
        break;
      case "speech_level":
        setSpeechLevel(event.level as number || 0);
        break;
      case "processing":
        setState("planning");
        break;
      case "transcript":
        if (event.final) {
          setTranscript(event.text as string || "");
          onTranscriptRef.current?.(event.text as string || "");
        }
        break;
      case "response":
        setResponse(event.text as string || "");
        onResponseRef.current?.(event.text as string || "");
        break;
      case "tts_start":
        setState("speaking");
        break;
      case "tts_end":
        // Server handles transition; client follows
        setState("listening");
        break;
      case "tts_cancelled":
        setState("listening");
        break;
      case "interrupted":
        setState("listening");
        break;
      case "wake_configured":
        if (event.enabled) {
          setState("waiting_for_wake");
        } else {
          setState("idle");
        }
        break;
      case "error":
        setError(event.message as string || "Unknown error");
        setState("idle");
        break;
      case "disconnected":
        setConnected(false);
        setState("idle");
        break;
    }
  }, []);

  // Create client on mount
  useEffect(() => {
    const client = new VoiceClient({
      agent: options.agent,
      model: options.model,
      onEvent: handleEvent,
    });
    clientRef.current = client;

    if (options.autoConnect) {
      client.connect().catch(() => {});
    }

    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const connect = useCallback(async () => {
    await clientRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
  }, []);

  const startListening = useCallback(async (newMode?: VoiceMode) => {
    const client = clientRef.current;
    if (!client) return;
    if (!client.connected) {
      await client.connect();
    }
    const effectiveMode = newMode ?? (alwaysOn ? "always_on" : "push_to_talk");
    if (newMode) setMode(newMode);
    client.start(effectiveMode, options.agent, options.model);
    await client.startCapture();
  }, [alwaysOn, options.agent, options.model]);

  const stopListening = useCallback(() => {
    clientRef.current?.stop();
    clientRef.current?.stopCapture();
  }, []);

  const interrupt = useCallback(() => {
    clientRef.current?.interrupt();
  }, []);

  const speak = useCallback((text: string) => {
    clientRef.current?.speak(text);
  }, []);

  const configureVoice = useCallback((settings: { wake_word?: { enabled: boolean; phrase?: string } }) => {
    clientRef.current?.configure(settings);
  }, []);

  const toggleAlwaysOn = useCallback(() => {
    setAlwaysOn((prev) => !prev);
  }, []);

  return {
    connected,
    state,
    mode,
    transcript,
    response,
    speechLevel,
    error,
    alwaysOn,
    connect,
    disconnect,
    startListening,
    stopListening,
    interrupt,
    speak,
    configureVoice,
    toggleAlwaysOn,
  };
}
