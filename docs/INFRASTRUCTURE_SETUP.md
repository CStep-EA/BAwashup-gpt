# Bower Ag CowCare Tool — Infrastructure Setup Guide

> **Audience**: Org Admin / DevOps  
> **Last Updated**: 2026-06-19  
> **Status**: Beta v0.1.0

---

## Overview

The CowCare Tool requires these external services:

| Service | Purpose | Required? | Fallback |
|---------|---------|-----------|----------|
| Supabase | Auth + PostgreSQL + pgvector | **Yes** | None — app won't start |
| Anthropic (Claude) | LLM for chat + classification | **Yes** | Conversation returns "UNKNOWN" |
| Cloudflare R2 | Report DOCX storage, media uploads | No (for MVP) | Reports generate but don't persist to cloud |
| Redis | ARQ async video worker queue | No (for MVP) | Video analysis unavailable; chat/reports work fine |
| Sentry | Error monitoring | No | No crash reporting |

---

## 1. Supabase (Already Configured)

Your project: `fqsbscehrhopifrtgztf.supabase.co`

### Verify Connection
```bash
cd backend && python scripts/verify_connection.py
```

### Key Config
| Env Var | Where |
|---------|-------|
| `SUPABASE_URL` | Project Settings → API → URL |
| `SUPABASE_ANON_KEY` | Project Settings → API → anon/public |
| `SUPABASE_SERVICE_ROLE_KEY` | Project Settings → API → service_role (secret!) |

### User Management (SQL Editor)
To update your own profile to org_admin:
```sql
-- Find your user ID from auth.users
SELECT id, email FROM auth.users WHERE email = 'your@email.com';

-- Update (or insert) your profile
INSERT INTO profiles (id, full_name, role, active)
VALUES ('YOUR-UUID-HERE', 'Your Name', 'org_admin', true)
ON CONFLICT (id) DO UPDATE SET role = 'org_admin', full_name = 'Your Name';
```

---

## 2. Cloudflare R2 Storage

### What It's Used For
- Report DOCX file storage (`reports/{user_id}/{report_id}.docx`)
- Media uploads (images for Claude Vision analysis)
- Video uploads (for async frame extraction)

### Setup Steps

1. **Create R2 Bucket**
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → R2 → Create Bucket
   - Bucket name: `bowerag-media`
   - Region: Auto (or closest to Railway deployment)

2. **Create API Token**
   - R2 → Manage R2 API Tokens → Create API Token
   - Permissions: Object Read & Write
   - Specify bucket: `bowerag-media`
   - Copy: Access Key ID + Secret Access Key

3. **Get Account ID**
   - Cloudflare Dashboard → Overview → right sidebar → Account ID

4. **Set Environment Variables** (Railway)
   ```
   R2_ACCOUNT_ID=your-account-id
   R2_ACCESS_KEY_ID=your-access-key
   R2_SECRET_ACCESS_KEY=your-secret-key
   R2_BUCKET_NAME=bowerag-media
   ```

5. **Verify**
   ```bash
   cd backend && python scripts/test_r2.py
   ```

### Without R2
The app works fine without R2:
- Reports generate and return content but DOCX isn't persisted to cloud
- Image analysis processes images in memory (no permanent storage)
- Video upload returns HTTP 503 with a friendly message

---

## 3. Redis (ARQ Job Queue)

### What It's Used For
- Async video processing jobs (ffmpeg frame extraction → Claude Vision)
- Background task queue for long-running operations

### Option A: Railway Redis Add-on
1. Railway Dashboard → your project → New Service → Redis
2. Copy the `REDIS_URL` from the Redis service's Variables tab
3. Add to your backend service: `REDIS_URL=redis://default:PASSWORD@HOST:PORT`

### Option B: Upstash Redis (Serverless)
1. [upstash.com](https://upstash.com) → Create Database
2. Region: closest to Railway
3. Copy the Redis URL (starts with `redis://` or `rediss://`)
4. Add to Railway: `REDIS_URL=rediss://default:PASSWORD@HOST:PORT`

### Without Redis
- Chat, products, pricing, reports, admin — all work perfectly
- Only video analysis (async worker) is unavailable
- The `/media/analyze-video` endpoint returns a helpful message

---

## 4. Sentry Error Monitoring (Optional)

### Setup
1. [sentry.io](https://sentry.io) → Create 2 projects:
   - `bowerag-cowcare-api` (Python / FastAPI)
   - `bowerag-cowcare-ui` (JavaScript / React)

2. **Backend** (Railway):
   ```
   SENTRY_DSN=https://YOUR-KEY@oXXXXXX.ingest.sentry.io/XXXXXXX
   ```

3. **Frontend** (Vercel):
   ```
   VITE_SENTRY_DSN=https://YOUR-KEY@oXXXXXX.ingest.sentry.io/XXXXXXX
   ```

### Verify
- Backend: Sentry initializes on startup (check logs for `[Sentry] Initialized`)
- Frontend: Errors auto-reported to Sentry dashboard

---

## 5. Railway Deployment

### Environment Variables (Complete List)
```
# Required
SUPABASE_URL=https://fqsbscehrhopifrtgztf.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key
ANTHROPIC_API_KEY=sk-ant-api03-...
ENVIRONMENT=production
APP_VERSION=0.1.0-beta

# CORS — your Vercel frontend URL
ALLOWED_ORIGINS=https://your-app.vercel.app

# Optional (add when ready)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=bowerag-media
REDIS_URL=redis://...
SENTRY_DSN=https://...
```

### Deployment
- Root directory: `/backend`
- Build: Handled by `nixpacks.toml` (installs Python 3.11 + ffmpeg)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## 6. Vercel Deployment

### Environment Variables
```
VITE_SUPABASE_URL=https://fqsbscehrhopifrtgztf.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_URL=https://your-railway-url.up.railway.app
VITE_APP_VERSION=0.1.0-beta
VITE_SENTRY_DSN=https://... (optional)
```

### Settings
- Framework: Vite
- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `dist`

---

## 7. Supabase Auth Configuration

After deploying frontend:

1. **Supabase Dashboard** → Authentication → URL Configuration
2. Set **Site URL**: `https://your-app.vercel.app`
3. Add **Redirect URLs**:
   - `https://your-app.vercel.app/auth/callback`
   - `http://localhost:5173/auth/callback` (dev)

---

## 8. Post-Deploy Verification

```bash
# Health check
curl https://YOUR-RAILWAY-URL/health

# Governance check (requires valid JWT)
curl https://YOUR-RAILWAY-URL/governance/health \
  -H "Authorization: Bearer YOUR-TOKEN"

# Expected: {"status":"ok","product_count":108,"sellability_count":540,...}
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ANTHROPIC_API_KEY not set` | Missing env var | Add to Railway Variables |
| `R2 Credentials incomplete` | Missing R2 vars | Add all 4 R2 vars or ignore (graceful) |
| `Redis: not reachable` | No Redis configured | Add REDIS_URL or ignore (video only) |
| `CORS blocked` | Frontend URL not in ALLOWED_ORIGINS | Add Vercel URL to ALLOWED_ORIGINS |
| Login fails | Supabase Site URL wrong | Update Site URL + Redirect URLs |
| `401 Unauthorized` | Token expired or invalid | Re-login to get fresh token |
