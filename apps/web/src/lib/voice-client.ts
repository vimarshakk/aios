"use client";

export type VoiceMode = "push_to_talk" | "always_on" | "wake_word";

export type VoiceEvent =
  | { type: "ready" }
  | { type: "connected" }
  | { type: "disconnected" }
  | { type: "listening"; mode?: string }
  | { type: "stopped" }
  | { type: "silence_timeout" }
  | { type: "speech_level"; level?: number }
  | { type: "processing" }
  | { type: "transcript"; text?: string; final?: boolean }
  | { type: "response"; text?: string }
  | { type: "tts_start" }
  | { type: "tts_end" }
  | { type: "tts_cancelled" }
  | { type: "interrupted" }
  | { type: "wake_configured"; enabled?: boolean }
  | { type: "state"; state: string }
  | { type: "level"; value: number }
  | { type: "error"; message: string };

type VoiceEventListener = (event: VoiceEvent) => void;

/**
 * Minimal voice client stub.
 *
 * In production this connects to the gateway voice service over WebSocket.
 * For now it is a no-op placeholder that satisfies the build and can be
 * wired later without touching call sites.
 */
export class VoiceClient {
  private listeners = new Set<VoiceEventListener>();
  private socket: WebSocket | null = null;
  private url: string;
  private agent: string;
  private model: string;
  private mode: VoiceMode = "push_to_talk";

  constructor(opts: { url?: string; agent?: string; model?: string } = {}) {
    this.url = opts.url ?? "wss://localhost:8080/voice";
    this.agent = opts.agent ?? "default";
    this.model = opts.model ?? "default";
  }

  on(listener: VoiceEventListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(event: VoiceEvent) {
    for (const l of this.listeners) l(event);
  }

  getMode(): VoiceMode {
    return this.mode;
  }

  get connected(): boolean {
    return this.socket !== null;
  }

  setMode(mode: VoiceMode) {
    this.mode = mode;
    this.emit({ type: "state", state: "mode_changed" });
  }

  async connect(): Promise<void> {
    // Stub: does not establish a real connection.
    this.emit({ type: "connected" });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.emit({ type: "disconnected" });
  }

  start(): void {
    this.emit({ type: "state", state: "listening" });
  }

  stop(): void {
    this.emit({ type: "state", state: "idle" });
  }

  sendAudio(_chunk: ArrayBuffer): void {
    // Stub: no-op
  }

  interrupt(): void {
    this.emit({ type: "interrupted" });
  }

  speak(_text: string): void {
    this.emit({ type: "tts_start" });
  }

  configure(_settings: { wake_word?: { enabled: boolean; phrase?: string } }): void {
    this.emit({ type: "wake_configured", enabled: _settings.wake_word?.enabled ?? false });
  }
}

export default VoiceClient;
