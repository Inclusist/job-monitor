# Railway Hourly Cron Setup Instructions

**Goal:** Set up the hourly job collection cron service on Railway

---

## ✅ What's Already Done

1. ✅ Procfile updated with hourly cron configuration
2. ✅ Hourly job script tested locally (collected 227 jobs!)
3. ✅ Enrichment agent integrated (adds AI metadata to jobs)

---

## 📋 Railway Setup Steps

### Step 1: Push Changes to GitHub

```bash
cd /Users/prabhu.ramachandran/job-monitor

# Add changes
git add Procfile scripts/hourly_job_cron.py scripts/enrich_missing_jobs.py

# Commit
git commit -m "feat: Add hourly job collection with enrichment agent

- Updated Procfile to run hourly cron instead of daily
- Hourly cron uses Active Jobs DB 1-hour endpoint
- Integrated enrichment agent (50 jobs per run)
- Tested locally: collected 227 jobs in last hour"

# Push to GitHub
git push origin main
```

### Step 2: Configure Railway Cron Service

1. **Log in to Railway Dashboard**
   - Go to https://railway.app
   - Select your project

2. **Add Cron Service** (if not already added)
   - Click "New Service"
   - Select "Empty Service" or "Worker"
   - Name it: `hourly-cron` or `cron`

3. **Configure Cron Service**
   - Go to service settings
   - Under "Service" tab:
     - **Start Command:** (Leave blank - Railway will use Procfile)
     - **Service Type:** Worker
   - Under "Deploy" tab:
     - Connect to your GitHub repo
     - Select branch: `main`

4. **Set Environment Variables**

   Make sure these are set (should inherit from project):
   - ✅ `DATABASE_URL` - PostgreSQL connection string
   - ✅ `ACTIVEJOBS_API_KEY` - Active Jobs DB API key
   - ✅ `ANTHROPIC_API_KEY` - Claude API key for enrichment

5. **Deploy**
   - Railway will automatically detect the `cron` process in Procfile
   - It will start running hourly job collection

---

## 🔍 How It Works

### Procfile Configuration

```procfile
web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
cron: python scripts/hourly_job_cron.py --interval 60
```

- **web:** Your Flask app (main website)
- **cron:** Hourly job collection service (runs every 60 minutes)

### Cron Workflow

**Every Hour:**
1. Fetches jobs from Active Jobs DB (1-hour endpoint)
2. Stores new jobs in `jobs` table (deduplicates automatically)
3. Runs enrichment agent on 50 jobs without AI metadata
4. Logs statistics and quota usage

**Example Output:**
```
📥 Collecting jobs from last hour...
  ✓ Fetched 227 jobs from API

✅ Hourly job completed successfully!
   • New jobs added: 227
   • Duplicates skipped: 0
   • API quota used: 227
   • Total jobs in database: 4,133

🤖 Enrichment agent starting...
   • Enrichment Agent: Processed 50 (Success: 50, Failed: 0)
```

---

## 📊 Monitoring

### Check Railway Logs

1. Go to Railway Dashboard
2. Select your `cron` service
3. Click on "Logs" tab
4. You should see hourly runs with output like above

### Check Database

```bash
# Check job count
python -c "from dotenv import load_dotenv; load_dotenv(); import psycopg2, os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM jobs'); print(f'Total jobs: {cursor.fetchone()[0]:,}')"

# Check jobs from today
python -c "from dotenv import load_dotenv; load_dotenv(); import psycopg2, os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM jobs WHERE DATE(discovered_date) = CURRENT_DATE'); print(f'Jobs today: {cursor.fetchone()[0]:,}')"
```

---

## ⚙️ Configuration Options

### Change Collection Interval

If you want to collect more or less frequently:

**In Procfile:**
```procfile
# Every 30 minutes (more frequent)
cron: python scripts/hourly_job_cron.py --interval 30

# Every 2 hours (less frequent)
cron: python scripts/hourly_job_cron.py --interval 120
```

### Adjust Enrichment Limit

**In scripts/hourly_job_cron.py (line 149):**
```python
# Current: 50 jobs per hour
enrich_stats = enrich_jobs(agent_conn, limit=50)

# More aggressive: 100 jobs per hour
enrich_stats = enrich_jobs(agent_conn, limit=100)

# Conservative: 25 jobs per hour
enrich_stats = enrich_jobs(agent_conn, limit=25)
```

**Note:** Each enrichment uses Claude API quota (~$0.001 per job with Haiku)

---

## 🎯 Expected Results

### Job Collection Rate
- **Hourly endpoint:** 50-300 jobs/hour typical
- **Daily accumulation:** 1,200-7,200 jobs/day
- **Deduplication:** Automatic (based on `external_id`)

### API Quota Usage

**Active Jobs DB (Ultra Plan):**
- Hourly collections: ~10-20 API calls/hour
- Jobs fetched: 100-300 jobs/hour
- Monthly quota: Should stay well within limits

**Claude API (Enrichment):**
- 50 enrichments/hour
- ~1,200 enrichments/day
- Cost: ~$1.20/day with Haiku ($0.001/job estimate)

---

## ✅ Success Criteria

After deployment, you should see:

1. **Railway Logs:**
   - Hourly runs appearing in logs
   - "Hourly job completed successfully" messages
   - Job counts increasing

2. **Database:**
   - Job count growing hourly
   - `discovered_date` shows recent timestamps
   - Jobs have AI metadata (from enrichment)

3. **Web App:**
   - New jobs appearing on homepage
   - "Discovered today" count increasing
   - Statistics updating

---

## 🐛 Troubleshooting

### Cron Service Not Starting

**Problem:** Service shows "crashed" or doesn't start

**Solutions:**
1. Check Railway logs for errors
2. Verify environment variables are set
3. Check Procfile syntax (no tabs, correct spacing)

### No Jobs Being Collected

**Problem:** Logs show "No new jobs in the last hour"

**This is normal!** The 1-hour endpoint only shows jobs posted in last 60 minutes. Some hours may have few or no new jobs.

### Enrichment Failing

**Problem:** "Enrichment Agent failed" in logs

**Solutions:**
1. Check `ANTHROPIC_API_KEY` is set correctly
2. Verify Claude API quota is available
3. Check database connection (jobs table exists)

### API Quota Exceeded

**Problem:** "Rate limit hit" or "Quota exhausted"

**Solutions:**
1. Check Active Jobs DB dashboard for quota status
2. Reduce collection frequency (increase interval)
3. Wait for quota reset (monthly)

---

## 📝 Summary

**What You Need to Do:**

1. ✅ Commit and push changes to GitHub
2. ✅ Configure Railway cron service (if not already)
3. ✅ Verify environment variables are set
4. ✅ Deploy and monitor logs

**What Happens Automatically:**

- ✅ Collects jobs every hour from Active Jobs DB
- ✅ Deduplicates automatically
- ✅ Enriches 50 jobs/hour with AI metadata
- ✅ Logs statistics and quota usage

---

**Ready to Deploy!** 🚀

Push your changes and Railway will handle the rest.
