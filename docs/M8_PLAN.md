# M8 — Voice Experience

**Objective:** Deliver a true conversational assistant with continuous voice interaction.

**Status:** In Progress

---

## Sub-milestones

| ID | Name | Priority | Status |
|----|------|----------|--------|
| M8.1 | Voice Service Foundation | High | Pending |
| M8.2 | Always-On Voice (VAD) | High | Pending |
| M8.3 | Wake Word | Medium | Pending |
| M8.4 | Interruptible TTS | High | Pending |
| M8.5 | Voice Overlay UI | Medium | Pending |
| M8.6 | Voice Workspace | Medium | Pending |

---

## M8.1 — Voice Service Foundation

### Objective
Wire existing voice engines (KokoroTTS, WhisperSTT, SileroVAD) into a live WebSocket audio pipeline between frontend and gateway.

### Architecture

```
Browser                          Gateway (FastAPI)
  │                                   │
  │── WS /ws/voice ──────────────────►│
  │   (binary: Float32 PCM 16kHz)     │
  │                                   ├── SileroVAD.is_speech()
  │                                   ├── WhisperSTT.transcribe()
  │                                   ├── Orchestrator.route()
  │                                   ├── KokoroTTS.synthesize()
  │                                   │
  │◄── WS events (JSON) ─────────────│
  │   { type: "transcript", ... }     │
  │   { type: "tts_start", ... }      │
  │   { type: "tts_audio", data: b64 }│
  │   { type: "tts_end", ... }        │
  │   { type: "response", ... }       │
  │   { type: "error", ... }          │
```

### Protocol

**Client → Server (binary):**
- Raw Float32 PCM samples, 16kHz, mono
- Sent every ~200ms (3200 samples per chunk)

**Client → Server (JSON control):**
```json
{ "type": "start", "mode": "push_to_talk" | "always_on", "agent": "default", "model": "" }
{ "type": "stop" }
{ "type": "speak", "text": "optional text to speak" }
{ "type": "interrupt" }
```

**Server → Client (JSON events):**
```json
{ "type": "listening" }
{ "type": "speech_start" }
{ "type": "transcript", "text": "hello", "final": true }
{ "type": "response", "text": "Hi there!" }
{ "type": "tts_start", "text": "Hi there!" }
{ "type": "tts_audio", "data": "<base64 float32>", "sample_rate": 24000 }
{ "type": "tts_end" }
{ "type": "error", "message": "..." }
```

### Tasks
1. Add `ws/voice` WebSocket endpoint to gateway
2. Lazy-load voice engines on first connection
3. Buffer incoming audio, run VAD, accumulate speech segments
4. On speech end → STT → orchestrator → TTS → stream audio back
5. Frontend: `VoiceClient` class for WS + audio capture
6. Frontend: `useVoiceStream` hook wrapping VoiceClient
7. Wire into CommandBar mic button (replace Web Speech API)

### Definition of Done
- User clicks mic → speaks → sees transcript → hears TTS response
- Audio flows over WebSocket, not browser-native APIs
- Latency < 2s for short utterances on local models

---

## M8.2 — Always-On Voice

### Objective
Enable VAD-driven always-on listening mode where AIOS automatically detects when the user starts speaking.

### Tasks
1. Server-side VAD state machine: idle → listening → processing → speaking
2. Auto-transition on speech_start/speech_end events
3. Frontend: always-on mode toggle in CommandBar
4. Visual feedback: listening indicator, speech level meter
5. Silence timeout (configurable, default 3s) → return to idle

### Definition of Done
- Toggle "Always Listening" in CommandBar
- Speak without pressing any button
- AIOS detects start/end of speech automatically
- Visual indicator shows listening/processing/speaking states

---

## M8.3 — Wake Word

### Objective
Detect a configurable wake word before entering active listening mode.

### Tasks
1. Integrate openWakeWord (Python)
2. Add wake word detection stage before VAD
3. Configurable hotword (default: "AIOS")
4. Enable/disable toggle
5. Frontend: wake word status indicator

### Definition of Done
- Say "AIOS" to activate listening
- Wake word detection runs server-side
- Configurable via Settings workspace

---

## M8.4 — Interruptible TTS

### Objective
Allow the user to interrupt the assistant mid-speech for natural conversation flow.

### Tasks
1. Frontend: detect user speech during TTS playback → send "interrupt" event
2. Server: cancel in-progress TTS synthesis
3. Barge-in: stop audio playback immediately
4. Continuous conversation loop (multi-turn without restart)
5. Push-to-talk mode (hold key to speak, release to send)
6. Context retention across turns (session memory)

### Definition of Done
- User can interrupt AIOS mid-sentence
- AIOS stops speaking and listens immediately
- Multi-turn conversations maintain context
- Push-to-talk works with Space bar hold

---

## M8.5 — Voice Overlay UI

### Objective
Provide visual feedback for voice interactions across the desktop shell.

### Tasks
1. Floating microphone button (always visible, bottom-right)
2. Live transcript overlay (shows what AIOS hears in real-time)
3. Audio waveform visualization (canvas-based)
4. Status indicator (idle/listening/thinking/speaking)
5. Smooth transitions between states

### Definition of Done
- Floating mic button visible on all workspaces
- Live transcript shows interim results
- Waveform animates during listening
- Status indicator reflects pipeline state

---

## M8.6 — Voice Workspace

### Objective
Dedicated workspace for voice-first interactions with full conversation history.

### Tasks
1. New "Voice" workspace in sidebar
2. Voice transcript panel (full conversation history)
3. Audio waveform display
4. Streaming text display
5. Planner progress integration
6. Voice settings (model, voice, sensitivity)

### Definition of Done
- Voice workspace accessible via sidebar
- Shows full voice conversation history
- Integrates with existing planner/goal system
- Settings for voice preferences

---

## Dependencies

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| TTS | kokoro-onnx | 0.9+ | Local TTS engine |
| STT | faster-whisper | 1.1+ | Local STT engine |
| VAD | silero-vad | 6.0+ | Voice activity detection |
| Wake Word | openwakeword | latest | Wake word detection |
| Audio | sounddevice | 0.5+ | Mic capture (server-side fallback) |
| Audio | numpy | 2.0+ | Audio processing |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Model download size | Lazy-load models on first use |
| CPU usage on low-end machines | Configurable model sizes (tiny/base/small) |
| Latency on CPU-only | Use ONNX for TTS, int8 for STT |
| Browser audio limitations | Web Audio API for capture, AudioContext for playback |
| WebSocket disconnection | Auto-reconnect with exponential backoff |
