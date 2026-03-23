# 002: Voice vs Text Input Method Tracking

**Date**: 2026-03-23
**Status**: Implemented
**Context**: `sendText()` always sent `input_method: 'text'` to the backend, even after voice transcription. This corrupts research data — we can't distinguish user-typed text from voice-transcribed text.

## Decision
Add a `lastInputMethod` flag. Set to `'voice'` when transcription succeeds, reset to `'text'` after send or clear. The flag is captured before reset and passed to the API call.

## Why this matters
This is a **research data integrity** issue, not just a UI bug. The field experiment needs to know which messages came from voice vs text input to analyze usage patterns across treatment arms.

## Backend support
Already in place: `InputMethod` enum in `models/message.py` accepts `'voice'` and `'text'`. No backend changes needed.
