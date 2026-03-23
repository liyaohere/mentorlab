# 003: Drawer Navigation (Replace Conversation List Screen)

**Date**: 2026-03-23
**Status**: Implemented
**Context**: Users had to click "+" on a conversation list to start chatting. For our target users (refugee entrepreneurs with limited smartphone experience), this added unnecessary friction.

## Decision
- Remove the standalone conversation list screen
- After login, go directly to the most recent conversation (or create new if none)
- Add a slide-out drawer (hamburger menu ☰) for conversation history
- Drawer contains: conversation list (active highlighted), "+ New" button, "Log out"

## UX rationale
- One less screen to navigate = lower cognitive load
- Voice-first users want to start talking immediately
- Conversation history is secondary — accessible but not blocking

## Implementation
- `enterApp()` function: fetches conversations, opens latest or creates new
- Drawer opens on ☰ tap, closes on outside tap or conversation selection
- No more `screen-convs` — only `screen-login` and `screen-chat`
