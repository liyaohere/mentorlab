# MentorLab Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (or Docker)
- Anthropic API key
- OpenAI API key (for Whisper voice transcription)

## Quick Start (Docker)

The fastest way to get everything running:

```bash
cd mentorlab

# 1. Copy env file and add your API keys
cp backend/.env.example backend/.env
# Edit backend/.env → set ANTHROPIC_API_KEY and OPENAI_API_KEY

# 2. Start database + backend
docker compose up -d

# 3. Run database migration
docker compose exec backend alembic upgrade head

# 4. Seed test data
docker compose exec backend python -c "
import asyncio
import sys; sys.path.insert(0, '.')
from scripts_seed import seed
asyncio.run(seed())
"

# 5. Backend is at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Manual Setup (without Docker)

### Backend

```bash
cd mentorlab/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Create PostgreSQL database
createdb mentorlab

# Run migrations
alembic upgrade head

# Seed test data
cd .. && python scripts/seed_test_data.py && cd backend

# Start server
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Mobile App

```bash
cd mentorlab/app

# Install dependencies
npm install

# Start Expo development server
npx expo start

# Scan the QR code with Expo Go on your phone
# Or press 'a' for Android emulator, 'i' for iOS simulator
```

**Important**: Update `API_URL` in `src/utils/constants.ts` to point to your backend. For development on a physical device, use your computer's local IP (e.g., `http://192.168.1.100:8000`).

### Admin Panel

```bash
cd mentorlab/admin

# Install dependencies
npm install

# Start development server
npm run dev
# Opens at http://localhost:5173
```

## Test Invite Codes

After seeding, these codes are available:

| Code | Arm | Cohort |
|------|-----|--------|
| `TEST001A` | control | pilot_test |
| `TEST002B` | analytic | pilot_test |
| `TEST003C` | constructive | pilot_test |

## Running Tests

```bash
cd mentorlab/backend
source .venv/bin/activate
pytest tests/ -v
```

## Building the APK

```bash
cd mentorlab/app

# Install EAS CLI
npm install -g eas-cli

# Login to Expo
eas login

# Build preview APK (for testing)
eas build --platform android --profile preview

# Build production APK
eas build --platform android --profile production
```

The APK will be available for download from the EAS dashboard.
