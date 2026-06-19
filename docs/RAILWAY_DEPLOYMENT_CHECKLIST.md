# Railway Backend Deployment — Sprint 18D Checklist

## Prerequisites

- [ ] Sprint 17D code fixes committed and pushed (CORS, health endpoint, governance block)
- [ ] GitHub repository: `CStep-EA/BAwashup-gpt`
- [ ] Railway account created at [railway.app](https://railway.app)
- [ ] All API keys/credentials ready (see Part 2 of Deployment Guide v3)

---

## Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub Repo**
2. Select: `CStep-EA/BAwashup-gpt`
3. Railway will auto-detect the repo

---

## Step 2: Configure Service Settings

In Railway → Service → **Settings**:

| Setting | Value |
|---------|-------|
| **Root Directory** | `/backend` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |
| **Health Check Timeout** | `300` (seconds) |
| **Restart Policy** | On failure (max 3 retries) |

> Note: Railway auto-detects Python via `requirements.txt`. The `nixpacks.toml` ensures `ffmpeg` is installed.

---

## Step 3: Set Environment Variables

In Railway → Service → **Variables**, add ALL of the following:

| Variable | Value | Source |
|----------|-------|--------|
| `SUPABASE_URL` | `https://your-project.supabase.co` | Supabase → Settings → API |
| `SUPABASE_ANON_KEY` | (long JWT) | Supabase → Settings → API → anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | (long JWT) | Supabase → Settings → API → service_role |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | [console.anthropic.com](https://console.anthropic.com) |
| `R2_ACCOUNT_ID` | (32-char hex) | Cloudflare Dashboard → right sidebar |
| `R2_ACCESS_KEY_ID` | (from R2 token creation) | Cloudflare R2 → Manage API Tokens |
| `R2_SECRET_ACCESS_KEY` | (from R2 token creation) | Cloudflare R2 → Manage API Tokens |
| `R2_BUCKET_NAME` | `bowerag-media` | Must match exactly |
| `APP_VERSION` | `0.1.0-beta` | Static value |
| `ENVIRONMENT` | `production` | Static value |
| `ALLOWED_ORIGINS` | *(leave empty — set after Vercel deploy)* | Fill in Sprint 19D |
| `SENTRY_DSN` | *(leave empty — set after Sentry setup)* | Fill in Sprint 20D |

---

## Step 4: Add Redis Add-On

1. In your Railway project, click **+ New** → **Database** → **Redis**
2. Railway auto-injects `REDIS_URL` into your service's environment
3. No manual configuration needed

---

## Step 5: Deploy

1. Click **Deploy** (or Railway auto-deploys on push)
2. Watch the build log — should show:
   - `nixpacks` detecting Python
   - `ffmpeg` installing from Nix
   - `pip install -r requirements.txt` completing
   - `uvicorn` starting on port `$PORT`
3. Wait for green checkmark (2-5 minutes)

---

## Step 6: Verify Deployment

### 6a. Health Check

```bash
curl https://YOUR-APP.railway.app/health
```

**Expected response:**
```json
{"status":"ok","service":"bowerag-cowcare-api","version":"0.1.0-beta","environment":"production"}
```

### 6b. Check Railway Logs

Look for these startup messages (no error loops):
```
[Startup] Bower Ag CowCare API v0.1.0-beta (production)
[Startup] ✅ Supabase: N locations found
[Startup] ✅ ffmpeg: ffmpeg version ...
[Startup] ✅ ANTHROPIC_API_KEY is set
[Startup] ✅ R2 storage: bucket reachable
[Startup] ✅ Redis: connected
[Startup] Startup validation complete.
```

### 6c. CORS Verification

```bash
# Should NOT allow evil.com
curl -s -I -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS https://YOUR-APP.railway.app/health

# Should NOT have: access-control-allow-origin: https://evil.com
```

### 6d. Auth Guard

```bash
# Should return 401 (no auth token)
curl -s -o /dev/null -w '%{http_code}' https://YOUR-APP.railway.app/products
# Expected: 401
```

---

## Step 7: Run Smoke Tests

Once deployed, run the full smoke test suite:

```bash
API_URL=https://YOUR-APP.railway.app bash scripts/production_smoke_test.sh
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `Module not found` | Root Directory not set | Settings → Root Directory → `/backend` |
| `SUPABASE_URL not set` | Missing env var | Variables → check spelling |
| `ffmpeg not found` | Missing nixpacks.toml | Verify `backend/nixpacks.toml` exists |
| Health check fails | Timeout too low | Already set to 300s in railway.toml |
| Continuous restarts | Bad env var or missing dependency | Check Railway logs for error |

---

## Post-Deployment Notes

- **ALLOWED_ORIGINS**: Set this to your Vercel URL after Sprint 19D (Vercel deployment)
- **SENTRY_DSN**: Set this after Sprint 20D (Sentry setup)
- Railway auto-redeploys on every push to the connected branch
- The worker service (for video processing) is deployed separately — see Sprint 18D Part 2
