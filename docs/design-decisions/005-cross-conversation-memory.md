# 005: Cross-Conversation Memory

**Date**: 2026-03-23
**Status**: Implemented
**Context**: The AI mentor had no continuity between conversations. Each conversation started fresh with only static participant data (name, venture, industry). Users expected the mentor to "remember" what they discussed before.

## Decision
Lazy summarization + accumulated memory model:

1. **`Conversation.summary`** (Text): 2-3 sentence summary generated after a conversation ends.
2. **`Participant.memory_notes`** (Text): Accumulated knowledge about the participant, updated with each summarized conversation.
3. **Trigger**: When a new conversation is created, summarize all unsummarized past conversations (lazy/on-demand). Update participant.memory_notes with extracted facts.
4. **Injection**: memory_notes is included in the system prompt under "What You Know From Previous Conversations".

## Why this approach
- **No extra API calls during chat** — summarization happens only at conversation creation time
- **Accumulated, not per-conversation** — memory_notes is a single growing document, not N separate summaries, keeping the system prompt compact
- **Structured by Claude** — the AI organizes memory by topic and removes duplicates each time
- **Graceful failure** — if summarization fails, conversation still works (just without memory)

## Alternatives considered
- **Per-message memory extraction**: Rejected — doubles API calls during every exchange
- **Vector embeddings / RAG**: Rejected — overengineered for ~450 participants with <50 conversations each
- **Include full past conversation history**: Rejected — would blow context window

## Research implications
- memory_notes is NOT exposed to the frontend (no participant manipulation)
- The field is auditable — can be queried to understand what the AI "knows"
- Memory is arm-agnostic — all arms accumulate memory equally
