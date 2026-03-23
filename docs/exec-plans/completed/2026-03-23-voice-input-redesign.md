# Plan: Voice Input Debug & Redesign

**Created**: 2026-03-23
**Status**: Completed
**Engineer**: Xilan (prompted by user report: "voice button not visible/not working")

## Goal
Fix 6 bugs in the voice input area and redesign it with a state machine + visual polish.

## Approach
1. Replace scattered state functions with centralized `setInputState()` (5 states)
2. Fix input_method tracking for research data integrity
3. Fix CSS positioning, audio format detection, timer off-by-one
4. Add Olo-style breathing glow animation on voice button
5. Add browser compatibility (auto-detect audio format, graceful fallback)

## Progress log
- [x] CSS: voice button 72→80px, idle-glow animation, text-container positioning
- [x] HTML: remove inline styles from "use voice" button
- [x] JS: add lastInputMethod, voiceSupported, audio format detection
- [x] JS: implement setInputState() state machine
- [x] JS: fix toggleRecord (voiceSupported guard, audio format, timer)
- [x] JS: fix transcribe (state machine, error handling, lastInputMethod)
- [x] JS: fix sendText (input_method tracking)
- [x] Backend: fix voice.py content-type validation (strip codec params)
- [x] UX: replace conversation list with drawer navigation
- [x] UX: auto-enter latest conversation after login

## Decisions made
- See docs/design-decisions/001 through 004
- Chose to always show voice button even on HTTP (alert on tap) rather than hiding it — users should see the full UI
- Hardcoded invite code for local dev testing (skipping invite code step temporarily)

## Artifacts
- Modified: `backend/static/app/index.html` (428 → 526 lines)
- Modified: `backend/app/routers/voice.py` (content-type validation fix)
