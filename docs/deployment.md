# MentorLab Deployment Guide

## Recommended Architecture

```
[Participants' Phones]
        |
    [Internet / 3G]
        |
[Backend API - Railway/VPS]  ←→  [PostgreSQL - Railway/VPS]
        |                              |
   [Claude API]              [S3/R2 - Audio Storage]
   [Whisper API]
   [FCM - Push Notifications]
        |
[Admin Panel - Cloudflare Pages]
[Download Page - Cloudflare Pages]
```

## Option A: Railway (Recommended for Pilot)

**Cost**: ~$5-20/month

1. Create a Railway project at [railway.app](https://railway.app)
2. Add a PostgreSQL database service
3. Add a service from your GitHub repo (point to `backend/` directory)
4. Set environment variables from `.env.example`
5. Railway auto-deploys on git push

```bash
# Set Railway env vars
railway variables set ANTHROPIC_API_KEY=sk-ant-xxx
railway variables set OPENAI_API_KEY=sk-xxx
railway variables set JWT_SECRET_KEY=$(openssl rand -hex 32)
# ... etc
```

## Option B: VPS (More Control)

**Cost**: ~$5-10/month (Hetzner, DigitalOcean)

```bash
# On your VPS:
git clone <your-repo> mentorlab
cd mentorlab

# Copy and configure .env
cp backend/.env.example backend/.env
nano backend/.env  # Add API keys, set JWT_SECRET_KEY

# Start with Docker Compose
docker compose up -d

# Run migrations
docker compose exec backend alembic upgrade head

# Set up reverse proxy (Caddy is simplest)
sudo apt install caddy
```

Caddyfile:
```
api.mentorlab.app {
    reverse_proxy localhost:8000
}
```

## Admin Panel Deployment

Build and deploy as static files to Cloudflare Pages:

```bash
cd admin
VITE_API_URL=https://api.mentorlab.app npm run build
# Upload dist/ to Cloudflare Pages
```

## APK Distribution

1. Build the APK: `cd app && eas build --platform android --profile production`
2. Download the APK from EAS
3. Host the APK file on Cloudflare Pages alongside the download page
4. Share the download link via WhatsApp to field coordinators

## Database Backups

```bash
# Manual backup
./scripts/backup_db.sh

# Automated daily backup (add to crontab)
crontab -e
# Add: 0 2 * * * cd /path/to/mentorlab && ./scripts/backup_db.sh
```

## Firebase Setup (Push Notifications)

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Add an Android app with package name `app.mentorlab`
3. Download `google-services.json` → place in `app/`
4. Generate a service account key → save as `backend/firebase-credentials.json`
5. Set `FCM_CREDENTIALS_PATH=./firebase-credentials.json` in backend `.env`

## S3/R2 Setup (Audio Storage)

Using Cloudflare R2 (free egress):

1. Create an R2 bucket named `mentorlab-audio` at [dash.cloudflare.com](https://dash.cloudflare.com)
2. Generate API tokens with R2 read/write permissions
3. Set in backend `.env`:
   ```
   S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
   S3_BUCKET_NAME=mentorlab-audio
   S3_ACCESS_KEY=<your-access-key>
   S3_SECRET_KEY=<your-secret-key>
   ```

## Monitoring

- **API docs**: `https://api.mentorlab.app/docs` — interactive Swagger UI
- **Health check**: `GET /health` — returns `{"status": "ok"}`
- **Admin dashboard**: `https://admin.mentorlab.app` — engagement metrics
- **Logs**: `docker compose logs -f backend` or Railway dashboard

## Pilot Checklist

- [ ] Backend deployed and accessible
- [ ] PostgreSQL running with migrations applied
- [ ] Anthropic API key set and working
- [ ] OpenAI API key set (for voice)
- [ ] Firebase configured (for push notifications)
- [ ] R2/S3 configured (for audio storage)
- [ ] Admin panel deployed
- [ ] Test participants uploaded via CSV
- [ ] APK built and hosted on download page
- [ ] Test: register with invite code, chat, voice input, push notification
- [ ] Test: admin dashboard shows data, export works
- [ ] Backup script running on schedule
- [ ] Share download link with field coordinators
