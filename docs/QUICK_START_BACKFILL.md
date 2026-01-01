# Quick Start: Backfill System

Complete setup guide for the user backfill and daily job loading system.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Job Monitor System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                    │
│  │  User Signup │ ──────> │  Backfill    │ (1 month)          │
│  │  + CV Upload │         │  Service     │                     │
│  └──────────────┘         └──────────────┘                     │
│                                   │                             │
│                                   ▼                             │
│                          ┌──────────────────┐                  │
│                          │  PostgreSQL DB   │                  │
│                          │  • Jobs          │                  │
│                          │  • User Queries  │                  │
│                          │  • Tracking      │                  │
│                          └──────────────────┘                  │
│                                   ▲                             │
│                                   │                             │
│  ┌──────────────┐         ┌──────────────┐                    │
│  │  Daily Cron  │ ──────> │  Daily Job   │ (24 hours)         │
│  │  (6 AM CEST) │         │  Loader      │                     │
│  └──────────────┘         └──────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Database:** PostgreSQL configured
2. **API Keys:**
   - JSearch API key (RapidAPI)
   - Active Jobs DB API key (RapidAPI)
   - Anthropic API key (for CV parsing)
3. **Environment:** Python 3.13+ with venv

---

## Step 1: Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install all dependencies (including APScheduler)
pip install -r requirements.txt
```

---

## Step 2: Run Database Migrations

### Migration 1: Normalize User Queries

Creates normalized `user_search_queries` table (title×location as separate rows):

```bash
python scripts/migrate_normalize_user_queries.py
```

**Expected output:**
```
MIGRATION: Normalize user_search_queries table
✓ Table already exists, columns already added
✅ Migration completed successfully!
```

### Migration 2: Add Backfill Tracking

Creates `backfill_tracking` table to track which combinations are backfilled:

```bash
python scripts/migrate_add_backfill_tracking.py
```

**Expected output:**
```
MIGRATION: Add backfill tracking table
📝 Creating backfill_tracking table...
✅ Migration completed successfully!
```

---

## Step 3: Configure Environment Variables

Ensure `.env` file has:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/job_monitor

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
JSEARCH_API_KEY=...
ACTIVEJOBS_API_KEY=...

# Flask
SECRET_KEY=<random-string>
FLASK_ENV=development
```

---

## Step 4: Test Backfill System (Optional)

Test with two users to verify deduplication works:

```bash
python scripts/test_backfill_flow.py
```

**What it does:**
1. Creates User 1 with search queries
2. Runs backfill for User 1 (fetches 1 month of jobs)
3. Creates User 2 with overlapping queries
4. Runs backfill for User 2 (skips already-backfilled combinations!)

**Expected output:**
```
TEST 1: Create User 1 with Unique Queries
✓ Created 4 query rows (2 titles × 2 locations = 4 rows)
✓ User 1 has 4 unbacked combinations

TEST 2: Backfill User 1
✓ Backfill completed for User 1:
   - Jobs added: 150

TEST 3: Create User 2 with Overlapping Queries
✓ Created 2 query rows (1 title × 2 locations = 2 rows)
✓ User 2 has 1 unbacked combinations  <-- Deduplication works!
   ✅ DEDUPLICATION WORKS!
      Expected 1 unbacked, got 1
      'Data Scientist in Berlin' already backfilled by User 1
```

---

## Step 5: Verify CV Upload Integration

The backfill is automatically triggered when users upload CVs.

**Test it:**

1. Start Flask app:
```bash
python app.py
```

2. Upload a CV via web UI or API:
```bash
curl -X POST http://localhost:8080/upload-cv \
  -F "cv=@test_cv.pdf" \
  -F "user_email=test@example.com"
```

3. Check logs for backfill trigger:
```
✓ Auto-generated 4 search query rows for test@example.com
  Combinations: 2 titles × 2 locations = 4 rows

🔄 Triggering 1-month backfill for test@example.com...
✓ Backfill completed: 150 jobs added
```

---

## Step 6: Set Up Daily Cron Job

### Option A: Local Testing (Run Once)

```bash
python scripts/daily_job_cron.py --run-once
```

**Output:**
```
DAILY JOB STARTED - 2024-01-15 14:30:00 CET
📥 Loading jobs from last 24 hours...

Query Analysis:
  Total query rows: 8
  Unique combinations: 5
  ✅ Quota saved: 3 API calls (37.5%)

✅ Daily job completed successfully!
   • Unique combinations: 5
   • Jobs fetched: 450
   • New jobs added: 380
```

### Option B: Run as Cron Service (Continuous)

```bash
python scripts/daily_job_cron.py --schedule "6:00"
```

**Output:**
```
DAILY JOB CRON SERVICE
Schedule: Every day at 6:00 CEST
Started: 2024-01-15 14:30:00

✓ Scheduled daily job at 6:00 CEST
  Next run: 2024-01-16 06:00:00+01:00

Press Ctrl+C to stop the service
```

---

## Step 7: Deploy to Railway

See [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) for complete deployment guide.

**Quick summary:**

1. **Create Railway project** → Connect GitHub repo
2. **Deploy web service:**
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Env: All API keys + `DATABASE_URL`
3. **Deploy cron service:**
   - Start: `python scripts/daily_job_cron.py --schedule "6:00"`
   - Env: `ACTIVEJOBS_API_KEY`, `DATABASE_URL`, `TZ=Europe/Berlin`
4. **Add PostgreSQL database** → Auto-connects to both services
5. **Run migrations** (via web service build command)

---

## How It Works

### User Signup Flow

```
User uploads CV
    ↓
Claude parses CV → Extracts desired titles, locations, preferences
    ↓
Queries auto-generated → Stored as normalized rows
    ↓
Check backfill_tracking → Which combinations are NEW?
    ↓
Backfill NEW combinations only → Fetch 1 month of jobs
    ↓
Mark as backfilled → Future users with same queries skip this!
```

### Daily Updates Flow

```
Cron triggers at 6 AM CEST
    ↓
Get unique combinations across ALL users (SELECT DISTINCT)
    ↓
Fetch last 24 hours for each unique combination
    ↓
Deduplicate and store jobs
    ↓
All users see fresh jobs
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/jobs/user_backfill.py` | Backfill service (1 month) |
| `scripts/user_query_loader.py` | Daily job loader (24h) |
| `scripts/daily_job_cron.py` | Cron scheduler |
| `src/cv/cv_handler.py` | CV upload + backfill trigger |
| `src/database/postgres_cv_operations.py` | DB methods for queries & tracking |
| `scripts/migrate_normalize_user_queries.py` | Migration 1 |
| `scripts/migrate_add_backfill_tracking.py` | Migration 2 |
| `scripts/test_backfill_flow.py` | Test script |

---

## Database Tables

### user_search_queries
Stores normalized query combinations per user

```sql
SELECT * FROM user_search_queries WHERE user_id = 1;

id | user_id | title_keyword      | location | ai_work_arrangement
1  | 1       | Data Scientist     | Berlin   | Remote OK
2  | 1       | Data Scientist     | Hamburg  | Remote OK
3  | 1       | ML Engineer        | Berlin   | Remote OK
4  | 1       | ML Engineer        | Hamburg  | Remote OK
```

### backfill_tracking
Tracks which combinations are backfilled globally

```sql
SELECT * FROM backfill_tracking;

id | title_keyword      | location | backfilled_date      | jobs_found
1  | Data Scientist     | Berlin   | 2024-01-15 10:30:00 | 45
2  | Data Scientist     | Hamburg  | 2024-01-15 10:35:00 | 32
3  | ML Engineer        | Berlin   | 2024-01-15 10:40:00 | 28
```

---

## Monitoring

### Check Quota Usage

Daily job prints quota analysis:
```
Quota Analysis (Ultra Plan: 20,000 jobs/month):
  This run used: 450 jobs (2.3% of quota)
  Projected monthly: 450/day × 30 = 13,500 jobs/month
  ✓ Good! Projected 68% quota utilization
```

### Check Deduplication Savings

```
Query Analysis:
  Total query rows: 10
  Unique combinations: 6
  ✅ Quota saved: 4 API calls (40%)
```

### View Backfill Status

```bash
# Check which combinations are backfilled
psql $DATABASE_URL -c "SELECT title_keyword, location, jobs_found FROM backfill_tracking ORDER BY backfilled_date DESC LIMIT 10;"
```

---

## Troubleshooting

### Issue: Migrations already run

**Symptom:**
```
✓ Table already exists, columns already added
```

**Solution:** This is normal! Migrations are idempotent (safe to run multiple times)

---

### Issue: Backfill not triggering on CV upload

**Check:**
1. CV successfully parsed? (Check logs for "✓ Auto-generated N search query rows")
2. Queries created? (Check `user_search_queries` table)
3. API keys set? (Check `.env` file)

**Debug:**
```bash
# Check user queries
psql $DATABASE_URL -c "SELECT * FROM user_search_queries WHERE user_id = 1;"

# Check backfill tracking
psql $DATABASE_URL -c "SELECT * FROM backfill_tracking;"
```

---

### Issue: Daily cron not running

**Check:**
1. Is the service running? (Check logs)
2. Correct timezone? (Should be `Europe/Berlin`)
3. Next run time correct? (Check scheduler logs)

**Test manually:**
```bash
python scripts/daily_job_cron.py --run-once
```

---

## Quota Optimization Tips

1. **Reduce pages per query:**
   - Edit `src/jobs/user_backfill.py` → Line 185: `num_pages=3` (instead of 5)
   - Edit `scripts/user_query_loader.py` → Line 165: `num_pages=1` (already optimized)

2. **Filter low-priority combinations:**
   - Set `priority=0` for less important queries
   - Modify loader to skip priority < 5

3. **Increase daily update frequency:**
   - Run daily updates twice a day (6 AM + 6 PM)
   - Reduce backfill depth to 2 weeks instead of 1 month

4. **Monitor overlap:**
   - More users with similar interests = more savings
   - Track deduplication % in daily logs

---

## Next Steps

After setup:

1. ✅ **Test locally** with test users
2. ✅ **Deploy to Railway** (both web + cron services)
3. ✅ **Monitor quota usage** for first few days
4. ✅ **Adjust settings** if quota too high/low
5. ✅ **Add more cities** as users from new locations join

---

## Support Documents

- [NORMALIZED_QUERIES.md](./NORMALIZED_QUERIES.md) - How normalization works
- [BACKFILL_SYSTEM.md](./BACKFILL_SYSTEM.md) - Detailed backfill documentation
- [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) - Deployment guide
- [API_FILTERS.md](./API_FILTERS.md) - API-level filtering guide

---

## Summary

You now have:
- ✅ Normalized query system for deduplication
- ✅ Backfill tracking to prevent duplicate fetches
- ✅ Automatic backfill on CV upload
- ✅ Daily cron job for fresh jobs
- ✅ Ready for Railway deployment

**Key benefit:** The more users with similar interests, the more quota you save!

First user: 100% quota used
Second user: ~50% quota used (50% overlap)
Third user: ~33% quota used (66% overlap)
...and so on!
