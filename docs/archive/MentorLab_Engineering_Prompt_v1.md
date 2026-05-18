# Project: AI Mentor RCT Platform — "MentorLab"

## What this is

A research platform for a 3-arm field experiment (~450 entrepreneurs, 6-8 weeks) testing how different cognitive modes of AI mentoring affect entrepreneurial strategy. Deployed as a **mobile app** in Uganda where internet is inconsistent and most interactions are researcher-initiated (the AI reaches out to the participant, not the other way around).

## The three arms

Each participant is assigned to exactly one arm. The ONLY difference between the treatment arms is the system prompt that governs AI behavior. The chat interface is identical across all three arms — participants should not know which arm they are in.

### Arm 1: Control (Structured Journaling)
- AI initiates contact each week with fixed template questions: "What did you work on this week?", "What progress did you make?", "What are your plans for next week?"
- AI responds ONLY with: acknowledgment + generic encouragement ("Thank you for sharing. Keep going!")
- AI provides ZERO domain knowledge, ZERO cognitive challenge, ZERO reflective listening
- No free-form conversation — only the template flow

### Arm 2: Analytic AI
- AI initiates weekly conversations with domain-relevant prompts
- AI acts as a knowledgeable business advisor that helps optimize within the entrepreneur's current strategic frame
- AI provides market data, competitor analysis, benchmarks, best practices
- AI NEVER challenges the entrepreneur's core assumptions or suggests reframing the problem
- AI treats the current strategic direction as given and helps improve execution within it
- Example: "Based on typical CAC in your vertical, you should aim for under $50" or "Your pricing is 20% above the market median for similar products"

### Arm 3: Constructive AI
- AI initiates weekly conversations with frame-challenging prompts
- AI has access to the SAME domain knowledge as Arm 2
- AI deploys knowledge to CHALLENGE and RESTRUCTURE the entrepreneur's frame
- AI uses "theorizing practices": thought experiments ("What would your business look like if...?"), recontextualization ("In the adjacent market, the pattern is..."), assumption-challenging ("Your data contradicts your assumption that...")
- AI still provides substantive information — it is NOT a hollow Socratic questioner
- Example: "You've described this as a product business, but your highest-margin customers are paying for implementation support. What if you reframed as a service business?"

## Core user flows

### Flow 1: Researcher initiates conversation (primary flow, ~80% of interactions)
1. Backend scheduler (cron job, configurable per cohort) triggers a new conversation for each active participant at the designated time (e.g., Monday 9am EAT)
2. The AI generates an opening message based on the participant's arm, venture context, and previous conversation history
3. Participant receives a **push notification**: "Your mentor has a new message for you"
4. Participant opens app → sees the new message → responds via text or voice
5. Conversation continues back and forth until natural conclusion

### Flow 2: Participant initiates conversation (allowed but secondary)
1. Participant opens app and taps "New conversation" or continues an existing thread
2. AI responds according to arm assignment
3. For Arm 1 (control), the AI gently redirects to the template: "I'd love to hear your update! Let's start with: what did you work on this week?"

### Flow 3: Voice input
1. Participant taps and holds the microphone button in the chat input area
2. Audio is recorded on-device
3. On release, audio is transcribed using Whisper API (or on-device speech recognition as fallback)
4. Transcribed text appears in the input field — participant can review/edit before sending
5. The AI receives and responds to the text (not the audio) — keeping all arms text-based for consistency
6. Original audio file is stored server-side for research purposes (transcript quality verification)

## Technical requirements

### App architecture
- **React Native** (via Expo) — single codebase for Android (primary) and iOS (secondary)
- **Distribution**: Generate a signed APK for Android that can be shared via WhatsApp/Telegram/direct download link for side-loading. No Google Play requirement. For iOS (if needed), use TestFlight or ad-hoc distribution
- **Minimum target**: Android 8+ (API 26), 2GB RAM, works on 3G connection

### Push notifications
- **Firebase Cloud Messaging (FCM)** for Android push notifications
- When the backend scheduler creates a new AI message, it simultaneously sends a push notification via FCM
- Notification text is generic and arm-blind: "Your mentor has a new message for you" (never reveals AI content in notification preview, to prevent shoulder-reading bias)
- If participant has notifications disabled, the message still appears when they open the app
- Track notification delivery and open rates per participant (engagement metric)

### Voice input / Speech-to-text
- **Primary**: OpenAI Whisper API (whisper-1 model)
  - Audio recorded on device as compressed format (opus/m4a, NOT wav — bandwidth matters)
  - Uploaded to backend → backend calls Whisper API → returns transcript
  - Latency budget: < 5 seconds for a 30-second utterance on 3G
  - Fallback for no connection: queue audio file, transcribe when connection returns
- **Fallback**: Android's built-in speech recognition (SpeechRecognizer API via expo-speech) for when the server is unreachable. This is less accurate but works offline
- **Language**: Set Whisper language parameter to English, but it handles code-switching (English + Luganda) reasonably well
- **Storage**: Store both the audio file and the transcript. Audio files are valuable research data (tone, hesitation, code-switching patterns) — store in object storage (S3-compatible)

### Offline resilience
- Messages typed/recorded offline are queued in local SQLite (on-device) with status: `pending`
- When connection returns, queued messages sync to server in order
- UI shows a subtle "waiting to send" indicator on pending messages (like WhatsApp's single gray checkmark)
- Previous conversation history is cached locally so participants can re-read past conversations offline
- The app should be usable (reading history, composing messages) even with no connection

### Backend
- **Runtime**: Node.js (Express or Fastify) or Python (FastAPI)
- **Database**: PostgreSQL
- **Object storage**: S3-compatible (e.g., Cloudflare R2, AWS S3, or MinIO on VPS) for audio files
- **AI provider**: Anthropic Claude API (claude-sonnet-4-20250514)
- **Scheduler**: Node-cron or Celery for triggering weekly AI-initiated conversations
- **Hosting**: Railway, Fly.io, or a VPS in a region close to East Africa (e.g., AWS af-south-1 Cape Town, or GCP europe-west1 which has decent latency to EA)

### Data model

```
participants
├── id (UUID)
├── invite_code (unique, used for initial registration)
├── arm (enum: control | analytic | constructive)
├── name
├── phone_number (for identity, not SMS — notifications go through FCM)
├── venture_name
├── venture_description (updated by participant over time)
├── industry_vertical
├── baseline_data (JSON: revenue, team_size, experience_years, cognitive_style_scores)
├── fcm_token (for push notifications, updated on each app launch)
├── created_at
├── cohort_id
└── status (enum: enrolled | active | completed | dropped)

conversations
├── id
├── participant_id (FK)
├── week_number
├── initiated_by (enum: system | participant)
├── created_at
└── ended_at

messages
├── id
├── conversation_id (FK)
├── role (enum: user | assistant | system)
├── content (text — the transcript if voice input)
├── input_method (enum: text | voice)
├── audio_file_url (nullable — S3 URL if voice input)
├── token_usage (JSON: {input_tokens, output_tokens} — for cost tracking)
├── created_at
├── sent_at (null if still queued offline)
└── sync_status (enum: synced | pending | failed)

surveys
├── id
├── participant_id (FK)
├── week_number
├── type (enum: baseline | weekly_pulse | midpoint | endline)
├── responses (JSON)
└── completed_at

notifications
├── id
├── participant_id (FK)
├── message_id (FK — the AI message that triggered the notification)
├── sent_at
├── delivered_at (from FCM delivery receipt)
├── opened_at (when participant tapped the notification)
└── status (enum: sent | delivered | opened | failed)

admin_events
├── id
├── admin_user_id
├── action (e.g., "randomized cohort", "exported data", "edited prompt")
├── metadata (JSON)
└── created_at
```

### System prompt structure

Each AI conversation starts with a system prompt assembled from components:

```
[ARM_INSTRUCTIONS]        ← Arm-specific behavioral rules (the core manipulation)
[PARTICIPANT_CONTEXT]     ← Venture description, industry, week number
[CONVERSATION_HISTORY]    ← Summary of key points from previous weeks
[KNOWLEDGE_CONTEXT]       ← Industry-specific market data (Arms 2 & 3 only)
[CONVERSATION_RULES]      ← Response length limits, language matching, safety rails
```

The [ARM_INSTRUCTIONS] block is the ONLY component that differs between arms. Everything else is identical for a given participant.

For the AI-initiated opening message, append:
```
[INITIATION_INSTRUCTION]  ← "Generate an opening message to start this week's conversation. 
                             Reference something specific from the participant's previous 
                             conversation to show continuity."
```

### Admin panel (researcher-facing, web-based)

- **Participant management**: Upload CSV with columns: name, phone, arm_assignment, cohort, industry_vertical. System generates invite codes and shareable registration links
- **Conversation monitor**: See all active conversations in real-time. Flag conversations where the AI may have broken arm protocol (e.g., analytic AI accidentally challenged an assumption). Searchable by participant, arm, week
- **Engagement dashboard**: 
  - Weekly active participants by arm
  - Average messages per conversation by arm
  - Voice vs text input ratio
  - Notification open rates
  - Dropout tracking with days-since-last-activity alerts
- **Data export**: 
  - All chat transcripts (CSV with columns: participant_id, arm, week, role, content, input_method, timestamp)
  - All survey responses
  - Audio files (bulk download by arm/week)
  - Engagement metrics
  - Token usage and cost report
- **System prompt editor**: Edit the three arm instruction templates. Shows diff before saving. Logs all changes with timestamps
- **Survey configuration**: Define questions for each survey type. Set trigger conditions (e.g., "show midpoint survey after week 3 conversation ends")
- **Scheduled sends**: Configure when AI-initiated conversations fire for each cohort (day of week, time of day, timezone)
- Protected by email + password login. Role-based: admin (full access) vs researcher (read-only + export)

### Key constraints

- **Budget**: 
  - Use claude-sonnet (not opus) for all participant-facing AI calls
  - Set max_tokens = 500 per AI response (enough for a substantive paragraph, not a wall of text)
  - Whisper API: ~$0.006/minute of audio — budget ~$0.03 per voice message (assuming ~5 min avg)
  - Estimate: ~450 participants × 7 weeks × 6 messages/week × $0.01/message ≈ **~$190 total AI cost**
  - Audio: ~450 × 7 × 3 voice messages × $0.03 ≈ **~$280 total Whisper cost**
  - Host: ~$20-50/month for a small VPS + database
- **Data integrity**: Every message stored server-side. Offline queue must resolve — no silent data loss. If sync fails 3 times, surface an error to the participant
- **Blinding**: UI identical across arms. App name, colors, icons — all the same. No arm-identifying text anywhere in the app. Even the admin panel should use arm codes (A/B/C) that can be remapped
- **Ethics/consent**: 
  - First screen after registration = informed consent (scrollable text + "I agree" checkbox)
  - Consent covers: chat data collection, audio recording, survey data, anonymous use in research
  - Participant can withdraw at any time (settings → "Leave study" → confirmation → marks status as dropped)
  - Audio recording has a separate consent toggle ("Allow voice messages to be recorded for research")
  - All consent events logged with timestamps
- **Language**: UI in English. AI responds in whatever language the participant uses. Whisper language hint set to English but handles code-switching

### APK distribution plan

Since we're side-loading (no Play Store):

1. Build signed APK via `eas build --platform android --profile preview`
2. Host the APK on a simple download page: `mentorlab.app/download`
3. Page detects platform — shows Android download button + installation instructions ("Open Settings → Allow unknown apps → Install")
4. Share the download link via WhatsApp groups / SMS to enrolled participants
5. For updates: app checks for new version on launch, shows "Update available" banner with download link
6. Version info stored in backend so admin can see which version each participant is running

## Development approach

### Monorepo structure
```
mentorlab/
├── app/                  ← React Native (Expo) mobile app
│   ├── src/
│   │   ├── screens/      ← Onboarding, Chat, Survey, Settings
│   │   ├── components/   ← MessageBubble, VoiceRecorder, SurveyForm
│   │   ├── services/     ← API client, offline queue, notification handler
│   │   ├── stores/       ← Local state (Zustand or similar)
│   │   └── utils/        ← Audio compression, text formatting
│   └── app.json          ← Expo config with FCM setup
├── backend/              ← API server
│   ├── routes/           ← /auth, /conversations, /messages, /surveys, /admin
│   ├── services/         ← Claude API wrapper, Whisper wrapper, FCM sender, scheduler
│   ├── prompts/          ← System prompt templates (version-controlled .md files)
│   │   ├── arm1_control.md
│   │   ├── arm2_analytic.md
│   │   ├── arm3_constructive.md
│   │   └── shared/
│   │       ├── conversation_rules.md
│   │       └── knowledge/          ← Per-industry knowledge files
│   │           ├── b2b_saas.md
│   │           ├── agribusiness.md
│   │           └── fintech.md
│   ├── jobs/             ← Scheduled conversation initiator, notification sender
│   └── middleware/       ← Auth, rate limiting, error handling
├── admin/                ← Web-based admin panel (React or simple Next.js app)
├── scripts/              ← Data export, randomization helpers, bulk invite generator
└── docs/                 ← Setup guide, prompt engineering notes, deployment runbook
```

### Build order (priority)

**Phase 1 — Core chat (week 1-2)**
1. Backend: auth (invite code registration), conversation & message CRUD, Claude API integration
2. App: registration flow, chat screen with text input, message sync
3. Test: one participant can register, chat with AI, messages persist

**Phase 2 — Three arms + voice (week 2-3)**
4. Backend: system prompt assembly with arm-specific instructions + participant context
5. App: voice recording button, audio upload, Whisper transcription flow
6. Test: three test participants (one per arm) get visibly different AI behavior; voice input works on a cheap Android phone

**Phase 3 — Notifications + scheduling (week 3-4)**
7. Backend: FCM integration, scheduled conversation initiator (cron)
8. App: push notification handler, "new message" indicator
9. Test: scheduled AI message fires at configured time, participant gets notification, taps to open conversation

**Phase 4 — Surveys + admin (week 4-5)**
10. App: survey screens (baseline, weekly pulse, midpoint, endline) triggered at correct times
11. Admin panel: participant upload, engagement dashboard, data export, prompt editor
12. Test: full participant lifecycle from registration through 2 simulated weeks

**Phase 5 — Polish + pilot (week 5-6)**
13. Offline queue hardening (test with airplane mode toggling)
14. APK signing and download page
15. Pilot with ~30 real participants in Kampala
16. Fix issues from pilot

## Success criteria for pilot readiness

1. ✅ A researcher uploads 30 participants with pre-assigned arms via admin CSV upload
2. ✅ Each participant installs the APK via WhatsApp link, registers with invite code, completes consent + onboarding
3. ✅ Monday 9am EAT: AI sends opening message to all active participants; push notifications arrive within 5 minutes
4. ✅ Participant can respond via text or voice; voice transcription returns in < 8 seconds on 3G
5. ✅ Chat history persists across app restarts and is readable offline
6. ✅ All three arms produce visibly different AI behavior that matches protocol
7. ✅ Messages composed offline sync correctly when connection returns
8. ✅ Admin can export all chat logs and survey data as CSV
9. ✅ Weekly pulse survey appears after each conversation
10. ✅ App runs smoothly on a Tecno Spark (or similar $100 Android phone) over 3G in Kampala
