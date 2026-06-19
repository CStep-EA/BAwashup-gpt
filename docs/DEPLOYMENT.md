# Bower Ag CowCare Tool — Deployment & Beta Launch Guide
## Sprint 16-19: v0.1.0-beta

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel (UI)   │────▶│  Railway (API)  │────▶│    Supabase     │
│  React 19 PWA   │     │  FastAPI + ARQ  │     │  PostgreSQL+RLS │
│  390px mobile   │     │  Claude Sonnet  │     │    pgvector     │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌──────────┐ ┌──────────┐
            │ Redis     │ │ R2       │ │ Sentry   │
            │ (ARQ)     │ │ (Media)  │ │ (Errors) │
            └───────────┘ └──────────┘ └──────────┘
```

---

## Step-by-Step Deployment

### 1. Railway Backend Deployment

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select the `BAwashup-gpt` repository
3. Set **Root Directory**: `/backend`
4. Railway auto-detects Python via `requirements.txt` + `nixpacks.toml`

**Add Environment Variables** (Railway → Variables):

| Variable | Source |
|----------|--------|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API |
| `ANTHROPIC_API_KEY` | Anthropic Console |
| `R2_ACCOUNT_ID` | Cloudflare R2 Dashboard |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 → API Tokens |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 → API Tokens |
| `R2_BUCKET_NAME` | `bowerag-media` |
| `REDIS_URL` | Railway Redis add-on (auto-populated) |
| `APP_VERSION` | `0.1.0-beta` |
| `ENVIRONMENT` | `production` |
| `ALLOWED_ORIGINS` | (set after Vercel deploy) |
| `SENTRY_DSN` | (set after Sentry setup) |

**Add Redis**:
- Railway → + New → Add-ons → Redis
- `REDIS_URL` is automatically added to environment

**Deploy** → Wait for green checkmark (2-5 minutes).

**Verify**:
```bash
curl https://bawashup-gpt-production.up.railway.app/health
# Expected: {"status":"ok","service":"bowerag-cowcare-api","version":"0.1.0-beta","environment":"production"}
```

---

### 2. Vercel Frontend Deployment

1. Go to [vercel.com](https://vercel.com) → Import Git Repository → `BAwashup-gpt`
2. Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

**Add Environment Variables** (Vercel → Settings → Environment Variables):

| Variable | Value |
|----------|-------|
| `VITE_SUPABASE_URL` | Same as backend `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | Same as backend `SUPABASE_ANON_KEY` |
| `VITE_API_URL` | `https://bawashup-gpt-production.up.railway.app` |
| `VITE_APP_VERSION` | `0.1.0-beta` |
| `VITE_SENTRY_DSN` | (set after Sentry setup) |

**Deploy** → Note your URL: `https://bowerag-cowcare.vercel.app`

**Post-Deploy**:
1. Go back to **Railway → Variables** → Update:
   ```
   ALLOWED_ORIGINS=https://bowerag-cowcare.vercel.app
   ```
   Click "Deploy" to apply.

2. Go to **Supabase → Authentication → URL Configuration**:
   - Site URL: `https://bowerag-cowcare.vercel.app`
   - Redirect URLs → Add: `https://bowerag-cowcare.vercel.app/auth/callback`

---

### 3. Worker Deployment (Video Processing)

In Railway, add a **second service** for the ARQ worker:

1. Railway → + New Service → Deploy from same GitHub repo
2. Set **Root Directory**: `/backend`
3. Set **Start Command**: `python -m app.workers.run_worker`
4. Copy ALL environment variables from the web service
5. Deploy

The worker processes video analysis jobs from the Redis queue.

---

### 4. Sentry Error Monitoring

1. Go to [sentry.io](https://sentry.io) → Create account (free tier)
2. Create **two projects**:

| Project | Platform | DSN Variable |
|---------|----------|--------------|
| `bowerag-cowcare-api` | Python/FastAPI | `SENTRY_DSN` (Railway) |
| `bowerag-cowcare-ui` | JavaScript/React | `VITE_SENTRY_DSN` (Vercel) |

3. Update Railway `SENTRY_DSN` with the Python project DSN → Redeploy
4. Update Vercel `VITE_SENTRY_DSN` with the JS project DSN → Redeploy

**Test Sentry**:
- Backend: Check Railway logs for "Sentry Initialized"
- Frontend: Open browser console on deployed site:
  ```js
  import * as Sentry from '@sentry/react'
  Sentry.captureException(new Error('Sprint 16 test'))
  ```
- Verify both events appear in Sentry dashboard

---

## Production Smoke Tests

Run after deployment:

```bash
# Set your actual URLs
export API_URL=https://bawashup-gpt-production.up.railway.app
export UI_URL=https://YOUR-PROJECT.vercel.app
export ADMIN_JWT=eyJ...  # Sign in as org_admin, get token from browser DevTools

bash scripts/production_smoke_test.sh
```

Expected: All 8 tests pass.

---

## Beta Launch Checklist

### GOVERNANCE
- [ ] `bash scripts/run_regression.sh` exits 0 against production
- [ ] All 10 governance regression tests pass on production endpoints
- [ ] Audit log reviewed: first 20 queries show no governance bypasses

### SECURITY
- [ ] CORS blocks requests from unknown origins (smoke test passed)
- [ ] Customer cannot navigate to /chat, /products, or /admin
- [ ] `git log -- .env` shows nothing (no secrets in git history)
- [ ] All env vars in Railway and Vercel — none hardcoded in source

### FUNCTIONALITY
- [ ] 3+ reps from different locations tested chat and product lookup
- [ ] At least 1 report generated, downloaded, and shared with test customer
- [ ] Test customer logged in and viewed shared report on mobile
- [ ] Admin/Manager can manage users without developer help
- [ ] Bug report filed from chat appears in admin bug tracker

### PERFORMANCE
- [ ] Pricing query average response < 4 seconds
- [ ] Troubleshooting query average < 6 seconds
- [ ] Page load time on mobile < 3 seconds (Chrome DevTools throttled)

### MONITORING
- [ ] Sentry receiving events from both API and UI
- [ ] No unhandled exceptions in Sentry from last 24 hours
- [ ] Railway logs show no repeated error patterns

### OPERATIONS
- [ ] Version log entry v0.1.0-beta created in admin portal
- [ ] Run book exists (this document)
- [ ] At least one Admin/Manager knows how to:
  - Invite a user
  - Resolve a bug report
  - Toggle a feature flag
  - Create a version log entry

---

## Operational Run Book

### How to update pricing
1. Export latest pricing sheet from ERP
2. Run: `python backend/scripts/migrate_pricing_sheets.py <file.xlsx>`
3. Verify: Login as consultant, query pricing for updated products
4. Monitor audit log for 24 hours

### How to add a user
1. Login as org_admin or admin_manager
2. Navigate to /admin/users → "Invite User"
3. Fill in email, role, full name
4. User receives email invitation from Supabase Auth

### How to check the audit log
1. Login as org_admin
2. Navigate to /admin/audit
3. Filter by date range, user, or action type
4. Export CSV for detailed analysis

### How to toggle a feature flag
1. Login as org_admin or admin_manager
2. Navigate to /admin/config
3. Find the flag (e.g., `feature.video_upload`)
4. Toggle value to `true` or `false`
5. Changes take effect within 60 seconds (cache TTL)

### How to create a version log entry
1. Login as org_admin
2. Navigate to /admin/versions → "Create New Release"
3. Fill in: version tag, release notes, breaking changes, bugs resolved
4. Click Create

---

## Important Warnings

⚠️ **Do NOT push the 150-user invite until every checklist item is checked.**

⚠️ **Keep the first beta group small (5-10 reps) for the first two weeks.**

⚠️ **Check the audit log DAILY during the first week for governance anomalies.**

⚠️ **The governance regression tests call real Claude API — run intentionally, not on CI.**

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| v0.1.0-beta | 2026-05-15 | Initial beta release |
| v0.1.0-beta | 2026-06-19 | Railway deployed, Vercel ready (Sprint 18D/19D) |
