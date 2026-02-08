# Backfill System Documentation

## Overview

The backfill system loads 1 month of historical jobs when a user signs up or updates their search parameters. It intelligently avoids re-fetching jobs that have already been loaded for other users with similar queries.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    New User Signs Up                    │
│                    Uploads CV                           │
└─────────────────────┬───────────────────────────────────┘
                      ▼
         ┌────────────────────────────┐
         │  1. CV Parsed by Claude    │
         │  2. Queries Auto-Generated │
         └────────────┬───────────────┘
                      ▼
         ┌────────────────────────────┐
         │  3. Store Normalized Rows  │
         │     in user_search_queries │
         └────────────┬───────────────┘
                      ▼
         ┌────────────────────────────────────┐
         │  4. Check backfill_tracking Table  │
         │     Which combos already fetched?  │
         └────────────┬───────────────────────┘
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
    ┌──────────┐            ┌────────────┐
    │ All Done │            │ New Combos │
    │ Already  │            │ Need Fetch │
    │ Fetched  │            └─────┬──────┘
    └──────────┘                  ▼
                       ┌──────────────────────┐
                       │ 5. Fetch from APIs   │
                       │    - JSearch (month) │
                       │    - ActiveJobs (7d) │
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ 6. Store Jobs in DB  │
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ 7. Mark as Backfilled│
                       │    in tracking table │
                       └──────────────────────┘
```

## Database Tables

### 1. user_search_queries (Normalized)

Stores each title×location combination as a separate row:

```sql
CREATE TABLE user_search_queries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    query_name TEXT,

    -- SINGLE values (not pipe-separated)
    title_keyword TEXT,
    location TEXT,

    -- Filters
    ai_work_arrangement TEXT,
    ai_employment_type TEXT,
    ai_seniority TEXT,
    ai_industry TEXT,

    -- Metadata
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Prevent duplicates
    UNIQUE(user_id, query_name, title_keyword, location,
           ai_work_arrangement, ai_employment_type,
           ai_seniority, ai_industry)
);
```

**Example:**
User wants "Data Scientist" + "ML Engineer" in "Berlin" + "Hamburg"

Creates **4 rows**:
```
user_id | title_keyword      | location
1       | Data Scientist     | Berlin
1       | Data Scientist     | Hamburg
1       | ML Engineer        | Berlin
1       | ML Engineer        | Hamburg
```

### 2. backfill_tracking

Tracks which combinations have been backfilled globally (across all users):

```sql
CREATE TABLE backfill_tracking (
    id SERIAL PRIMARY KEY,

    -- The combination
    title_keyword TEXT,
    location TEXT,
    ai_work_arrangement TEXT,
    ai_employment_type TEXT,
    ai_seniority TEXT,
    ai_industry TEXT,

    -- Metadata
    backfilled_date TIMESTAMP DEFAULT NOW(),
    jobs_found INTEGER DEFAULT 0,

    -- Prevent duplicates
    UNIQUE(title_keyword, location, ai_work_arrangement,
           ai_employment_type, ai_seniority, ai_industry)
);
```

**Example:**
```
title_keyword      | location | backfilled_date      | jobs_found
Data Scientist     | Berlin   | 2024-01-15 10:30:00 | 45
Data Scientist     | Hamburg  | 2024-01-15 10:35:00 | 32
ML Engineer        | Berlin   | 2024-01-15 10:40:00 | 28
```

## Flow Details

### User 1 Signs Up

**Step 1:** CV uploaded, queries generated:
```python
db.add_user_search_queries(
    user_id=1,
    query_name="Primary Search",
    title_keywords=["Data Scientist", "ML Engineer"],
    locations=["Berlin", "Hamburg"],
    ai_work_arrangement="Remote OK",
    ai_seniority="Senior"
)
# Creates 4 rows in user_search_queries
```

**Step 2:** Check what needs backfilling:
```python
unbacked = db.get_unbacked_combinations_for_user(user_id=1)
# Returns: All 4 combinations (none in backfill_tracking yet)
```

**Step 3:** Fetch jobs from APIs:
```python
# For each combination:
# - JSearch: date_posted="month" (1 month)
# - ActiveJobs: date_posted="week" (7 days, pagination for 1 month)
```

**Step 4:** Mark as backfilled:
```python
for combo in unbacked:
    db.mark_combination_backfilled(
        title_keyword=combo['title_keyword'],
        location=combo['location'],
        ai_work_arrangement=combo['ai_work_arrangement'],
        ai_seniority=combo['ai_seniority'],
        jobs_found=len(jobs)
    )
# Adds 4 rows to backfill_tracking
```

**Result:** 4 API calls made, ~150 jobs stored

---

### User 2 Signs Up (Overlapping Queries)

**Step 1:** CV uploaded, queries generated:
```python
db.add_user_search_queries(
    user_id=2,
    query_name="Primary Search",
    title_keywords=["Data Scientist"],  # Overlaps with User 1!
    locations=["Berlin", "Munich"],      # Berlin overlaps!
    ai_work_arrangement="Remote OK",
    ai_seniority="Senior"
)
# Creates 2 rows in user_search_queries
```

**Step 2:** Check what needs backfilling:
```python
unbacked = db.get_unbacked_combinations_for_user(user_id=2)
# Returns: Only 1 combination!
# - "Data Scientist in Munich" (NEW)
# - "Data Scientist in Berlin" (SKIP - already in backfill_tracking)
```

**Step 3:** Fetch jobs from APIs:
```python
# Only for "Data Scientist in Munich"
# 1 API call instead of 2!
```

**Step 4:** Mark new combination as backfilled:
```python
db.mark_combination_backfilled(
    title_keyword="Data Scientist",
    location="Munich",
    ...
)
# Adds 1 row to backfill_tracking
```

**Result:** 1 API call made (50% quota saved!), User 2 can still see all Berlin jobs from User 1's backfill

---

## API Usage

### JSearch API

```python
jobs = jsearch_collector.search_jobs(
    query="Data Scientist",
    num_pages=5,                 # 5 pages × 10 = 50 jobs
    date_posted="month",         # 1 MONTH!
    country="de"
)
```

**Quota:** 1 credit per job returned

### Active Jobs DB API

```python
jobs = activejobs_collector.search_jobs(
    query="Data Scientist",
    location="Berlin",
    num_pages=10,                # More pages for backfill
    results_per_page=100,
    date_posted="week",          # 7 days (can loop for 1 month)
    ai_work_arrangement="Remote OK",
    ai_seniority="Senior"
)
```

**Quota:** 1 credit per job returned

**Note:** Active Jobs DB doesn't have "month" filter, so we use "week" with pagination

---

## Deduplication Benefits

### Example Scenario: 10 Users

**Without Deduplication:**
- User 1: 4 combinations → 4 API calls
- User 2: 2 combinations → 2 API calls (overlap ignored)
- User 3: 3 combinations → 3 API calls (overlap ignored)
- ...
- **Total: 25 API calls**

**With Deduplication:**
- User 1: 4 new combinations → 4 API calls
- User 2: 1 new combination → 1 API call (1 overlap skipped!)
- User 3: 2 new combinations → 2 API calls (1 overlap skipped!)
- ...
- **Total: 12 API calls**

**Savings: 13 API calls (52%!)**

The more users with similar interests, the more savings!

---

## Daily Updates

After backfill, the daily cron job keeps jobs up-to-date:

```python
# Daily at 6 AM CEST
loader = UserQueryLoader(api_key, db)
stats = loader.load_jobs_for_all_users(date_posted='24h')
```

**How it works:**
1. Get all unique combinations across all users (using `SELECT DISTINCT`)
2. Fetch last 24 hours for each combination
3. Store new jobs
4. Users see fresh jobs daily

**Quota usage:** Much lower than backfill (only 24h of jobs, not 1 month)

---

## Usage

### Automatic (Production)

When user uploads CV, backfill runs automatically:

```python
# In cv_handler.py
if row_count > 0:  # Queries created
    from src.jobs.user_backfill import backfill_user_on_signup
    backfill_stats = backfill_user_on_signup(
        user_id=user_id,
        user_email=user_email,
        db=self.cv_manager
    )
```

### Manual (Testing)

```bash
# Test backfill for specific user
python scripts/test_backfill_flow.py

# Or programmatically
from src.jobs.user_backfill import backfill_user_on_signup
from src.database.factory import get_database

db = get_database()
stats = backfill_user_on_signup(
    user_id=1,
    user_email="user@example.com",
    db=db
)
```

---

## Monitoring

### Check Backfill Status

```python
# Get unbacked combinations for a user
unbacked = db.get_unbacked_combinations_for_user(user_id=1)

if not unbacked:
    print("All combinations already backfilled!")
else:
    print(f"Need to backfill {len(unbacked)} combinations")
```

### Check Backfill Tracking Table

```sql
SELECT
    title_keyword,
    location,
    backfilled_date,
    jobs_found
FROM backfill_tracking
ORDER BY backfilled_date DESC;
```

### View Quota Savings

Backfill service prints savings:
```
📊 Backfill Analysis:
  New combinations to backfill: 1
  (Other combinations already backfilled by other users)
```

---

## Quota Estimates

### Per-User Backfill

**Average user:**
- 3 title keywords × 2 locations = 6 combinations
- JSearch: 6 × 50 jobs = 300 credits
- ActiveJobs: 6 × 100 jobs = 600 credits
- **Total: ~900 credits per new user**

**With 50% overlap (typical):**
- First user: 900 credits
- Second user: ~450 credits (3 new combos)
- Third user: ~300 credits (2 new combos)
- Average: ~400 credits per user

### Monthly Quota (Ultra Plan: 20,000 jobs/month)

**New users:**
- 20,000 / 900 = ~22 new users per month (without overlap)
- 20,000 / 400 = ~50 new users per month (with 50% overlap)

**Plus daily updates:**
- Daily: ~500 jobs/day
- Monthly: 500 × 30 = 15,000 jobs
- Remaining for new users: 5,000 jobs
- New users: 5,000 / 400 = ~12 users/month

**Recommendation:**
- Monitor quota usage in backfill logs
- Adjust `num_pages` if quota becomes tight
- Upgrade to higher plan if onboarding > 10 users/month

---

## Best Practices

1. **Always check unbacked combinations first** - Don't blindly backfill all queries

2. **Mark combinations as backfilled immediately** - Prevent race conditions if multiple users sign up simultaneously

3. **Handle API errors gracefully** - If backfill fails, user can still use the app (daily updates will load jobs)

4. **Monitor quota projections** - Backfill service prints quota usage estimates

5. **Test with small datasets first** - Use `--run-once` flag on test users before production

6. **Use normalized queries** - Always store title×location as separate rows for deduplication

7. **Keep backfill_tracking up-to-date** - Don't delete rows unless you want to re-backfill

---

## Troubleshooting

### Issue: All Combinations Already Backfilled

**Symptom:**
```
✅ All combinations for user example@test.com already backfilled!
No new backfill needed - user can access existing jobs
```

**Cause:** Other users have same queries

**Solution:** This is GOOD! User can access existing jobs without using quota

---

### Issue: Backfill Fails with API Error

**Symptom:**
```
⚠️  Warning: Backfill failed: API rate limit exceeded
User can still use the app, jobs will load on next daily update
```

**Cause:** API quota exhausted or rate limit hit

**Solution:**
1. User can still browse jobs loaded by others
2. Daily cron will catch up next day
3. Consider upgrading API plan

---

### Issue: Jobs Not Showing for User

**Symptom:** User completed backfill but sees no jobs

**Cause:** Jobs stored but matching query not working

**Debug:**
```sql
-- Check if jobs exist
SELECT COUNT(*) FROM jobs WHERE location ILIKE '%Berlin%';

-- Check user queries
SELECT * FROM user_search_queries WHERE user_id = 1;

-- Check job matching logic in app
```

---

## Future Improvements

1. **Incremental backfill** - Only backfill gaps between last update and current date

2. **Priority-based backfill** - Backfill high-priority queries first

3. **Background processing** - Use Celery/RQ for async backfill

4. **Smart scheduling** - Backfill during off-peak API hours

5. **Backfill analytics** - Track which combinations have most overlaps

---

## Summary

The backfill system:
- ✅ Loads 1 month of historical jobs for new users
- ✅ Automatically deduplicates across users
- ✅ Saves 40-60% of API quota through smart tracking
- ✅ Integrates seamlessly with CV upload flow
- ✅ Falls back gracefully if APIs fail
- ✅ Scales efficiently as user base grows

**Key insight:** The more users with similar interests, the more quota savings!
