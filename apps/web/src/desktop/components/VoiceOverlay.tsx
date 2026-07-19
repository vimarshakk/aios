"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Volume2, X } from "lucide-react";
import { useVoiceStream } from "@/hooks/useVoiceStream";

export function VoiceOverlay() {
  const { state, disconnect, interrupt } = useVoiceStream();

  const isActive =
    state === "listening" ||
    state === "waiting_for_wake" ||
    state === "transcribing" ||
    state === "planning" ||
    state === "executing" ||
    state === "speaking";

  if (!isActive) return null;

  const stateLabel = {
    listening: "Listening…",
    waiting_for_wake: "Waiting for wake word",
    transcribing: "Transcribing…",
    planning: "Thinking…",
    executing: "Running…",
    speaking: "Speaking…",
  }[state] ?? state;

  const StateIcon =
    state === "speaking" ? Volume2 :
    state === "waiting_for_wake" ? MicOff :
    Mic;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50"
      >
        <div className="flex items-center gap-3 rounded-2xl border border-border bg-card/95 backdrop-blur-xl px-4 py-3 shadow-lg">
          <div className="flex items-center gap-2">
            <motion.div
              animate={
                state === "listening"
                  ? { scale: [1, 1.2, 1] }
                  : state === "speaking"
                    ? { opacity: [0.6, 1, 0.6] }
                    : {}
              }
              transition={{ repeat: Infinity, duration: 1.5 }}
            >
              <StateIcon className="h-4 w-4 text-muted-foreground" />
            </motion.div>
            <span className="text-sm text-muted-foreground">{stateLabel}</span>
          </div>

          <div className="h-4 w-px bg-border" />

          {state !== "waiting_for_wake" && (
            <button
              onClick={interrupt}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Interrupt
            </button>
          )}

          <button
            onClick={disconnect}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
