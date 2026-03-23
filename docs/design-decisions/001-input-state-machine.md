# 001: Input Area State Machine

**Date**: 2026-03-23
**Status**: Implemented
**Context**: Voice input button was reported invisible/non-functional. Root cause: scattered state management across `switchToVoice()`, `switchToText()` with incomplete cleanup of UI elements.

## Decision
Replace individual toggle functions with a centralized `setInputState(state)` function managing 5 discrete states:

```
VOICE_IDLE → RECORDING → TRANSCRIBING → TEXT_PREVIEW → (send) → VOICE_IDLE
                                                      → (clear) → VOICE_IDLE
VOICE_IDLE → TEXT_TYPING → (send) → VOICE_IDLE
```

`setInputState()` hides all elements first, then shows only what's needed for the target state. This eliminates orphaned UI elements.

## Alternatives considered
- Fix individual functions one by one: rejected because the cross-dependencies were error-prone
- Use a framework (React/Vue) for state management: rejected because single-file constraint is a project golden principle

## Consequences
- All input UI transitions go through one function — easier to debug and extend
- `switchToVoice()` and `switchToText()` kept as thin wrappers for onclick handlers
- New states can be added by extending the switch block
