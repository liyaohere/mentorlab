# MentorLab — Agent Map

## What is this
AI mentor chat app for a field experiment with Ugandan refugee entrepreneurs.
Voice-first PWA (single HTML file) + FastAPI backend + PostgreSQL.

## Quick start
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

## Key constraint
**Single-file frontend**: `backend/static/app/index.html` — pure HTML/CSS/JS, no frameworks.
Backend API is stable; most iteration happens on the frontend.

## Docs map (read what you need, not everything)

| Topic | File |
|-------|------|
| System architecture | [docs/architecture.md](docs/architecture.md) |
| UI spec & input design | [docs/app-ui-spec.md](docs/app-ui-spec.md) |
| Local setup | [docs/setup.md](docs/setup.md) |
| Deployment (Railway) | [docs/deployment.md](docs/deployment.md) |
| Design decisions log | [docs/design-decisions/](docs/design-decisions/) |
| Active execution plans | [docs/exec-plans/active/](docs/exec-plans/active/) |
| Completed plans | [docs/exec-plans/completed/](docs/exec-plans/completed/) |
| Structural lints | [scripts/lint-structure.sh](scripts/lint-structure.sh) |

## Architecture (one-paragraph summary)
Three-layer app: **Frontend** (single HTML, voice-first) → **FastAPI** (auth, conversations, messages, voice transcription) → **PostgreSQL** (participants, conversations, messages). Voice goes through OpenAI Whisper. AI responses via Claude API. See [docs/architecture.md](docs/architecture.md) for full details.

## Golden principles
1. **Voice-first input** — mic button is the default; text is fallback
2. **State machine for input** — all input UI transitions go through `setInputState()`
3. **Track input method** — every message records `input_method: 'voice'|'text'` for research data
4. **Mobile-first** — target: low-end Android on 3G. Test at 375px width
5. **No manual code** — prefer agent-written code; encode taste into lints, not memory

## Testing
- Local: `http://localhost:8000/` (voice needs HTTPS — use ngrok)
- Production: `https://mentorlab-api-production.up.railway.app/`
- Test invite code (local): check `psql -d mentorlab -c "SELECT code, arm FROM invite_codes WHERE NOT used;"`

## Agent self-validation (Chrome DevTools MCP)
After UI changes, the agent can validate its own work:
1. User runs: `./scripts/dev-chrome.sh` (launches Chrome with DevTools Protocol)
2. Agent uses `mcp__chrome-devtools__take_screenshot` to capture current state
3. Agent uses `mcp__chrome-devtools__evaluate_script` to check for JS errors
4. Agent uses `mcp__chrome-devtools__click` to test interactions
5. Agent uses `mcp__chrome-devtools__take_snapshot` to inspect DOM

**Validation checklist for UI changes:**
- Screenshot the page at 390x844 (iPhone SE size)
- Check `console.error` output via evaluate_script
- Test state transitions (voice idle → recording → transcribing → text preview)

## Admin panel validation
After admin/backend changes, run these checks:
```bash
./scripts/lint-structure.sh          # Structural lints (frontend + backend + docs)
./scripts/test-admin-api.sh          # Admin API smoke tests (all endpoints)
./scripts/test-admin-api.sh https://mentorlab-api-production.up.railway.app mentorlab2026  # Production
```
- Verify key elements are visible (voice button, messages, header)
- Test state transitions (voice idle → recording → transcribing → text preview)

## File structure (key paths)
```
backend/
├── static/app/index.html    ← THE frontend (single file)
├── app/
│   ├── main.py              ← FastAPI entry, router mounts
│   ├── routers/             ← auth, conversations, messages, voice, admin
│   ├── services/            ← claude_service, whisper_service
│   ├── models/              ← SQLAlchemy models
│   └── schemas/             ← Pydantic request/response
├── .env                     ← Local secrets (DO NOT COMMIT)
└── tests/
docs/
├── architecture.md
├── app-ui-spec.md
├── design-decisions/        ← Why we chose X over Y
├── exec-plans/              ← Active and completed plans
├── setup.md
└── deployment.md
scripts/
└── lint-structure.sh        ← Structural lints for agent code
```
