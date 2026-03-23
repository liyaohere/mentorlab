# Execution Plans

Plans are first-class artifacts in this repo. They capture intent, decisions, and progress for non-trivial work.

## Structure
- `active/` — Plans currently being worked on
- `completed/` — Finished plans (kept for decision history)

## Plan format
```markdown
# Plan: [Title]

**Created**: YYYY-MM-DD
**Status**: Active | Completed | Abandoned
**Engineer**: [who prompted this]

## Goal
What we're trying to achieve (1-2 sentences).

## Approach
How we're doing it.

## Progress log
- [ ] Step 1
- [x] Step 2 (completed YYYY-MM-DD)

## Decisions made
- Chose X over Y because Z

## Open questions
- ...
```

## When to create a plan
- Multi-step feature work (>3 distinct changes)
- Architectural changes
- Bug investigations that span multiple files
- NOT needed for: single-file fixes, typos, config changes
