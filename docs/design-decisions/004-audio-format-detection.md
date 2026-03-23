# 004: Browser Audio Format Auto-Detection

**Date**: 2026-03-23
**Status**: Implemented
**Context**: Audio format was hardcoded to `audio/webm`. Safari/iOS doesn't support webm in MediaRecorder, and the backend rejected `audio/webm;codecs=opus` because the content-type check was too strict.

## Decision
**Frontend**: Auto-detect best supported format via `MediaRecorder.isTypeSupported()`. Priority: webm/opus > webm > mp4 > ogg/opus > wav. Use detected type for MediaRecorder options, Blob type, and file extension.

**Backend**: Strip codec parameters (`;codecs=opus`) before checking against `ALLOWED_AUDIO_TYPES` in `voice.py`.

## Consequences
- Voice recording now works on Safari, iOS, and all Android browsers
- Backend accepts any format Whisper supports, regardless of codec string variations
