# 🚀 Tomorrow's Session - Quick Start Guide

**Date:** 2026-01-05
**Status:** Ready to test enhanced Claude matching

---

## 📋 What We Did Yesterday

1. ✅ Enhanced Claude prompt with AI metadata (skills, experience, industries)
2. ✅ Lowered Claude threshold from 70% → 50%
3. ✅ Fixed schema issues (`job_id` → `external_id`, removed `status` column)
4. ✅ Created `match_existing_jobs.py` script

**Full details:** See `SESSION_SUMMARY_2026-01-04.md`

---

## 🎯 First Thing Tomorrow: Run This Command

```bash
cd /Users/prabhu.ramachandran/job-monitor
python scripts/match_existing_jobs.py
```

### What This Will Do:
1. Load sentence transformer model (~10 seconds)
2. Run semantic matching on 3,882 jobs (~2-3 minutes)
3. Run enhanced Claude analysis on ≥50% matches (~5-10 minutes)
4. Save results to `user_job_matches` table
5. Display statistics

### Expected Output:
```
==========================================================
MATCHING EXISTING JOBS
==========================================================
User: your@email.com
User ID: 1
==========================================================

📊 Total jobs in database: 3,882
🔄 Starting full matching pipeline...

📥 Loading sentence transformer model...
✅ Model loaded (2.5s)

🔍 Semantic Matching...
✓ Found 350 matches above 30% threshold

🤖 Claude Analysis (125 high-scoring jobs)...
[Progress messages...]

✅ MATCHING COMPLETE
Matches found: 350
Jobs analyzed by Claude: 125
```

---

## ✅ If Command Succeeds

### Step 1: Check Web UI
1. Open browser → http://localhost:5000 (or your app URL)
2. Log in
3. Go to `/jobs` page
4. **Expected:** Jobs appear with match scores and reasoning

### Step 2: Verify Enhanced Matching
Click into a job detail page and check:

**Good Example (What We Want):**
```
Match Score: 78%
Priority: Medium

Key Alignments:
- Strong skill overlap: Python, SQL, Machine Learning, Data Analysis
- Experience level matches: 3-5 years required, you have 6 years
- Industry alignment: Technology

Potential Gaps:
- Missing: AWS, Kubernetes, Docker
- Limited cloud infrastructure experience

Reasoning: Strong technical match with 70% of required skills...
```

**Bad Example (Old System):**
```
Reasoning: Good alignment with your background.
```

### Step 3: Document Success
If it works well:
- [ ] Take screenshots of enhanced match analysis
- [ ] Note any improvements vs old system
- [ ] Check a few different jobs for consistency

---

## ❌ If Command Fails

### Common Errors & Fixes

#### Error 1: Schema Issues
```
psycopg2.errors.UndefinedColumn: column "job_id" does not exist
```
**Fix:** We missed a reference. Search for it:
```bash
grep -rn "job_id" src/database/postgres_operations.py
grep -rn "\.status" src/database/postgres_operations.py
```

#### Error 2: No User Found
```
❌ No users found in database
```
**Fix:** Upload a CV first via web UI at `/upload`

#### Error 3: No CV Profile
```
❌ No CV profile found
```
**Fix:** Re-upload CV to trigger parsing

#### Error 4: Claude API Error
```
Error: API quota exceeded
```
**Fix:** Check Anthropic dashboard for quota, or wait for reset

---

## 🔍 Things to Check Tomorrow

### 1. Match Quality
- [ ] Are skill matches specific? (e.g., "Python, SQL, ML")
- [ ] Are gaps specific? (e.g., "Missing: AWS, Kubernetes")
- [ ] Is experience comparison shown? (e.g., "5 years vs 3-5 required")
- [ ] Is industry alignment mentioned?

### 2. Performance
- [ ] How long does matching take?
- [ ] How many jobs get Claude analysis?
- [ ] Any timeout issues?

### 3. Coverage
- [ ] How many total matches found?
- [ ] What percentage get Claude analysis?
- [ ] Any jobs missing that should match?

### 4. Consistency
- [ ] Are similar jobs scored similarly?
- [ ] Is reasoning consistent across jobs?
- [ ] Are priority levels appropriate?

---

## 📁 Important Files Reference

### Scripts
- `scripts/match_existing_jobs.py` - Run matching on existing jobs (NEW)
- `scripts/hourly_job_cron.py` - Hourly job collection
- `scripts/filter_jobs.py` - OLD semantic matching (doesn't include Claude)

### Core Matching
- `src/matching/matcher.py` - Full matching pipeline (semantic + Claude)
- `src/analysis/claude_analyzer.py` - Enhanced Claude prompt (MODIFIED)

### Database
- `src/database/postgres_operations.py` - Database queries (FIXED schema issues)

### Documentation
- `SESSION_SUMMARY_2026-01-04.md` - Yesterday's detailed summary
- `MIGRATION_SUMMARY.md` - Overall project status
- `TOMORROW_START_HERE.md` - This file

---

## 💡 Quick Debugging Commands

### Check Database State
```bash
# Count jobs
python -c "from dotenv import load_dotenv; load_dotenv(); import psycopg2, os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM jobs'); print(f'Jobs: {cursor.fetchone()[0]:,}')"

# Count matches
python -c "from dotenv import load_dotenv; load_dotenv(); import psycopg2, os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM user_job_matches'); print(f'Matches: {cursor.fetchone()[0]:,}')"

# Get user email
python -c "from dotenv import load_dotenv; load_dotenv(); import psycopg2, os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cursor = conn.cursor(); cursor.execute('SELECT email FROM users'); print(f'User: {cursor.fetchone()[0]}')"
```

### Clear Matches and Start Fresh
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import psycopg2, os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cursor = conn.cursor(); cursor.execute('TRUNCATE TABLE user_job_matches RESTART IDENTITY CASCADE'); conn.commit(); print('✓ Cleared')"
```

---

## 🎯 Session Goals

**Primary Goal:** Get enhanced Claude matching working end-to-end

**Success Criteria:**
- ✅ Script runs without errors
- ✅ Jobs appear on web UI
- ✅ Match reasoning is specific and data-driven
- ✅ Users can see skill matches, gaps, and experience comparison

**Stretch Goals:**
- Test with CV re-upload
- Verify backfill workflow
- Optimize performance if needed
- Document improvements

---

**Ready to Start!** 🚀

Just run: `python scripts/match_existing_jobs.py`
