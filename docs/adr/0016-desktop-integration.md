# ADR-0016: Desktop Integration

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M3.6 added desktop integration capabilities for running agents on a local machine. This includes clipboard access, system notifications, file dialogs, and system information gathering. The subsystem enables agents to interact with the desktop environment.

## Decision

Four independent modules:

- **Clipboard:** Async clipboard read/write via subprocess (pbcopy/pbpaste on macOS, xclip on Linux, clip on Windows). Returns `ClipboardResult` with content and format.
- **Notifications:** `NotificationService` with `notify(title, message, urgency)` interface. `Urgency` enum (LOW, NORMAL, CRITICAL). Returns `NotificationResult`.
- **FileDialogs:** `show_dialog(mode, title, ...)` for open/save file dialogs. `DialogMode` enum (OPEN, SAVE, SELECT_DIR). Returns `FileDialogResult` with selected path(s).
- **SystemInfo:** `SystemInfoCollector` with `collect()` method returning `SystemInfo` (OS, version, CPU, memory, disk, display info).

## Consequences

- Desktop package depends ONLY on `aios-core` — not on distributed/telemetry
- Clipboard uses subprocess calls (no system-specific libs needed)
- Notifications use `notify-send` on Linux, `osascript` on macOS, `toast.exe` on Windows
- File dialogs use native OS dialogs (zenity/kdialog, osascript, PowerShell)
- System info uses `psutil`-like logic but done manually (no hard dependency)
- All I/O is async where possible (subprocess calls wrapped in async)

## Key Design Decisions

1. **No `@traced_task` decorators:** Desktop shouldn't depend on distributed package
2. **Subprocess-based clipboard:** Avoids native library dependencies
3. **Independent modules:** Each can be used standalone
4. **Cross-platform abstraction:** Same API works on macOS/Linux/Windows

## Alternatives Considered

1. **pyperclip for clipboard:** Good but doesn't support async well
2. **plyer for notifications:** Heavy, pulls many deps
3. **PyQt/PySide for dialogs:** Overkill for simple file selection

## References

- `packages/desktop/src/aios/desktop/clipboard.py`
- `packages/desktop/src/aios/desktop/notifications.py`
- `packages/desktop/src/aios/desktop/dialogs.py`
- `packages/desktop/src/aios/desktop/info.py`
- `tests/test_desktop.py`
