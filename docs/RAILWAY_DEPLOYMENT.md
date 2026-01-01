# Railway Deployment Guide - Two Services

This guide explains how to deploy both the **web application** and **daily cron job** as separate services on Railway from a single repository.

## Architecture

```
┌─────────────────────────────────────────────┐
│         Single GitHub Repository           │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────┐       ┌──────────────────┐
│  Web Service  │       │  Cron Service    │
│               │       │                  │
│  Flask App    │       │  Daily Job       │
│  Port: 8080   │       │  Runs at 6 AM    │
└───────────────┘       └──────────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
            ┌──────────────┐
            │  PostgreSQL  │
            │   Database   │
            └──────────────┘
```

## Why Two Services?

1. **Web Service**: Handles user requests, CV uploads, job browsing
2. **Cron Service**: Runs scheduled daily job to fetch new jobs (6 AM CEST)

**Railway allows multiple services from a single repository!**

---

## Step 1: Create Railway Project

1. Go to [Railway](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authenticate with GitHub
5. Select your `job-monitor` repository

---

## Step 2: Deploy Web Service

### 2.1 Create Web Service

1. Railway will auto-detect your Flask app
2. Name it: **"job-monitor-web"**

### 2.2 Configure Web Service

**Start Command:**
```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

**Environment Variables:**
```bash
# Database
DATABASE_URL=<from Railway PostgreSQL>

# Claude API
ANTHROPIC_API_KEY=<your-key>

# Job APIs
JSEARCH_API_KEY=<your-key>
ACTIVEJOBS_API_KEY=<your-key>

# Flask
FLASK_ENV=production
SECRET_KEY=<generate-random-string>

# Railway
PORT=8080
```

### 2.3 Build Settings

**Install Command:**
```bash
pip install -r requirements.txt
```

**Build Command:**
```bash
python scripts/migrate_normalize_user_queries.py && \
python scripts/migrate_add_backfill_tracking.py
```

---

## Step 3: Deploy Cron Service

### 3.1 Create Second Service

1. In your Railway project, click **"+ New"**
2. Select **"Empty Service"**
3. Name it: **"job-monitor-cron"**

### 3.2 Connect to Same Repository

1. In service settings, click **"Source"**
2. Select **"GitHub Repo"**
3. Choose your `job-monitor` repository
4. Railway will link to the same repo as the web service

### 3.3 Configure Cron Service

**Start Command:**
```bash
python scripts/daily_job_cron.py --schedule "6:00"
```

**Environment Variables:**
```bash
# Database (SAME as web service)
DATABASE_URL=<from Railway PostgreSQL>

# Job APIs (SAME as web service)
ACTIVEJOBS_API_KEY=<your-key>

# Timezone
TZ=Europe/Berlin
```

### 3.4 Build Settings

**Install Command:**
```bash
pip install -r requirements.txt && pip install -r requirements_cron.txt
```

**No build command needed** (migrations already run by web service)

---

## Step 4: Add PostgreSQL Database

### 4.1 Create Database

1. In Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Name it: **"job-monitor-db"**

### 4.2 Connect to Both Services

Railway will automatically provide `DATABASE_URL` to both services.

**Verify connection:**
1. Web service → Variables → Check `DATABASE_URL` exists
2. Cron service → Variables → Check `DATABASE_URL` exists

---

## Step 5: Test Deployment

### Test Web Service

```bash
# Check web service is running
curl https://job-monitor-web.railway.app/health

# Upload a CV (should trigger backfill)
curl -X POST https://job-monitor-web.railway.app/upload-cv \
  -F "cv=@test_cv.pdf" \
  -F "user_email=test@example.com"
```

### Test Cron Service

**View logs in Railway dashboard:**
1. Click on "job-monitor-cron" service
2. Go to "Deployments" tab
3. Click on latest deployment
4. View logs to see:
   - Service started
   - Scheduled time
   - Next run time

**Manual test (one-time run):**
```bash
# SSH into cron service (Railway CLI)
railway run python scripts/daily_job_cron.py --run-once
```

---

## Service Configuration Files

### Procfile (Optional - Railway auto-detects)

Create `Procfile` in repository root:

```
web: gunicorn app:app --bind 0.0.0.0:$PORT
cron: python scripts/daily_job_cron.py --schedule "6:00"
```

### railway.json (Optional - Advanced Configuration)

Create `railway.json` in repository root:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Note:** This applies to web service. For cron service, configure start command in dashboard.

---

## Monitoring

### View Logs

**Web Service:**
```bash
railway logs --service job-monitor-web
```

**Cron Service:**
```bash
railway logs --service job-monitor-cron
```

### Check Next Run Time

In cron service logs, you'll see:
```
✓ Scheduled daily job at 6:00 CEST
  Next run: 2024-01-15 06:00:00+01:00
```

### Monitor Quota Usage

Cron job prints quota usage after each run:
```
Quota Analysis (Ultra Plan: 20,000 jobs/month):
  This run used: 450 jobs (2.3% of quota)
  Projected monthly: 450/day × 30 = 13,500 jobs/month
  ✓ Good! Projected 68% quota utilization
```

---

## Environment Variables Summary

| Variable | Web Service | Cron Service | Source |
|----------|------------|--------------|--------|
| `DATABASE_URL` | ✅ | ✅ | Railway PostgreSQL |
| `ANTHROPIC_API_KEY` | ✅ | ❌ | Manual |
| `JSEARCH_API_KEY` | ✅ | ❌ | Manual |
| `ACTIVEJOBS_API_KEY` | ✅ | ✅ | Manual |
| `SECRET_KEY` | ✅ | ❌ | Manual (generate) |
| `PORT` | ✅ | ❌ | Railway (auto) |
| `TZ` | ❌ | ✅ | Manual |

---

## Cost Estimation

### Railway Plans

**Hobby Plan ($5/month):**
- 512MB RAM per service
- Shared CPU
- 100GB network
- ⚠️ **Sleeps after inactivity** (not suitable for cron)

**Developer Plan ($20/month):**
- 8GB RAM per service
- Shared CPU
- 100GB network
- ✅ **No sleep** (suitable for cron)

**Recommendation**: Use Developer Plan to ensure cron runs reliably.

---

## Deployment Checklist

- [ ] Create Railway project
- [ ] Deploy web service
  - [ ] Set start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
  - [ ] Add all environment variables
  - [ ] Verify builds successfully
- [ ] Deploy cron service
  - [ ] Set start command: `python scripts/daily_job_cron.py --schedule "6:00"`
  - [ ] Add environment variables (`DATABASE_URL`, `ACTIVEJOBS_API_KEY`, `TZ`)
  - [ ] Verify starts successfully
- [ ] Add PostgreSQL database
  - [ ] Verify both services can connect
- [ ] Run migrations
  - [ ] `migrate_normalize_user_queries.py`
  - [ ] `migrate_add_backfill_tracking.py`
- [ ] Test web service
  - [ ] Upload test CV
  - [ ] Verify backfill triggers
  - [ ] Check jobs in database
- [ ] Test cron service
  - [ ] View logs for next run time
  - [ ] Wait for scheduled run OR trigger manually
  - [ ] Verify jobs loaded from last 24h

---

## Troubleshooting

### Cron Service Not Running

**Check logs:**
```bash
railway logs --service job-monitor-cron --follow
```

**Common issues:**
- Missing `ACTIVEJOBS_API_KEY`
- Missing `DATABASE_URL`
- Wrong timezone (`TZ` should be `Europe/Berlin`)

### Web Service Can't Connect to Database

**Check:**
1. `DATABASE_URL` is set in environment variables
2. PostgreSQL service is running
3. Migrations have been run

### Backfill Not Triggering on CV Upload

**Check web service logs:**
```bash
railway logs --service job-monitor-web --follow
```

Look for:
```
🔄 Triggering 1-month backfill for user@example.com...
✓ Backfill completed: 50 jobs added
```

### Quota Exceeded

**Check daily job logs:**
```
⚠️  WARNING: Projected 120% OVER quota!
💡 Consider: Reduce max_results for some queries
```

**Solutions:**
- Reduce `num_pages` in `user_query_loader.py`
- Reduce `results_per_page` in `user_query_loader.py`
- Remove low-priority query combinations

---

## Next Steps

After deployment:

1. **Test end-to-end flow:**
   - New user signs up → Queries generated → Backfill runs → Jobs visible
   - Wait 24 hours → Daily cron runs → New jobs appear

2. **Monitor quota usage:**
   - Check cron logs daily for quota projections
   - Adjust query settings if approaching limit

3. **Scale as needed:**
   - Add more cities to user queries
   - Increase API quotas if needed
   - Upgrade Railway plan for more resources

---

## Support

**Railway Documentation:** https://docs.railway.app
**Railway Discord:** https://discord.gg/railway

**Project Issues:** Check `/docs` folder for additional documentation
