# Automatic Job Loading from Arbeitsagentur

This document explains the automatic job loading system that populates your database with jobs from the German Federal Employment Agency (Arbeitsagentur).

---

## Overview

The system provides two mechanisms for loading jobs:

1. **One-time Bulk Loader** - Populate your database with historical jobs for all existing users
2. **Automatic Triggers** - Load jobs automatically when users register or update preferences

Both use the FREE Arbeitsagentur API, which provides access to 150k-200k German jobs without any cost or registration.

---

## 1. One-Time Bulk Loader

### Purpose
Load jobs from the last 30 days for ALL existing users' keyword+location combinations.

### When to Use
- Initial database population
- After adding multiple users manually
- Periodic refresh to catch missed jobs

### How to Run

```bash
cd /path/to/job-monitor
python scripts/bulk_load_arbeitsagentur.py
```

### What It Does

1. **Aggregates Combinations**:
   - Queries all active users from database
   - Extracts their search keywords and locations
   - Falls back to config.yaml defaults if user has no preferences
   - Deduplicates combinations across all users

2. **Fetches Jobs**:
   - For each unique (keyword, location) pair:
     - Searches Arbeitsagentur API for jobs from last 30 days
     - Fetches up to 100 jobs per search
     - Parses and stores in database
   - Rate limits to 0.5s between searches (polite to API)

3. **Reports Progress**:
   - Shows real-time progress for each search
   - Displays statistics at the end:
     - Total combinations processed
     - Jobs fetched vs stored
     - Failed searches (if any)
     - Time elapsed

### Example Output

```
================================================================================
ARBEITSAGENTUR BULK LOADER
================================================================================

This script will:
1. Aggregate all keyword+location combinations from all users
2. Fetch jobs from Arbeitsagentur for each combination (last 30 days)
3. Store all jobs in the database

This is a ONE-TIME operation to populate your job database.
================================================================================

⚠️  Proceed with bulk load? (yes/no): yes

🔧 Initializing database...

================================================================================
AGGREGATING SEARCH COMBINATIONS FROM ALL USERS
================================================================================

📊 Found 3 active users
📋 Default config: 15 keywords, 3 locations

👤 User 1 (user1@example.com)
   Keywords: Data Scientist, Machine Learning Engineer, AI Researcher, ...
   Locations: Berlin, Munich, Hamburg

👤 User 2 (user2@example.com)
   Keywords: Software Engineer, Backend Developer, DevOps Engineer
   Locations: Germany

✅ Total unique combinations: 48

================================================================================
BULK LOADING JOBS FROM ARBEITSAGENTUR
================================================================================

🔍 Processing 48 unique keyword+location combinations
📅 Fetching jobs from last 30 days
⏱️  Estimated time: 96 seconds (~2s per search)

[1/48] Data Scientist in Berlin
   Used by 2 user(s): [1, 3]
   📊 Found 347 total results, fetched 100
   ✅ Stored 98/100 jobs

[2/48] Machine Learning Engineer in Munich
   Used by 1 user(s): [1]
   📊 Found 156 total results, fetched 100
   ✅ Stored 95/100 jobs

... (continues for all combinations)

================================================================================
BULK LOAD SUMMARY
================================================================================

📊 Statistics:
   Combinations processed: 48
   Jobs fetched: 4,234
   Jobs stored: 4,156
   Failed searches: 2
   Time elapsed: 124.5 seconds
   Average per search: 2.59s

✅ Bulk load complete!
================================================================================

🎉 All done! Check your database for new jobs.
```

### Error Handling

- **Failed Searches**: Listed at end of summary
- **Duplicate Jobs**: Automatically skipped by database unique constraints
- **API Errors**: Logged and script continues with next combination

---

## 2. Automatic Triggers

### Purpose
Automatically load jobs when:
- A new user registers
- A user updates their search preferences

### How It Works

#### Trigger 1: New User Registration

**When**: User completes registration form

**What Happens**:
1. User account is created
2. System loads default keywords/locations from `config.yaml`
3. Background job loading starts for all default combinations
4. User sees flash message: "Loading initial jobs in the background..."
5. Jobs appear in database within 30-60 seconds

**Code Location**: `app.py` line ~200-212

**Example**:
```python
# New user registers
user_id = cv_manager.register_user(email, password, name)

# Auto-trigger job loading with defaults
trigger_new_user_job_load(
    user_id=user_id,
    keywords=['Data Scientist', 'ML Engineer', ...],  # from config.yaml
    locations=['Berlin', 'Munich', 'Hamburg'],         # from config.yaml
    job_db=job_db
)
```

#### Trigger 2: Search Preferences Update

**When**: User updates keywords or locations in "Search Preferences" page

**What Happens**:
1. System captures OLD preferences
2. User saves NEW preferences
3. System calculates NEW combinations:
   - New keywords × all locations (old + new)
   - New locations × all keywords (old + new)
4. Background job loading starts for NEW combinations only
5. User sees flash message: "Loading jobs for new search combinations..."

**Code Location**: `app.py` line ~1393-1436

**Smart Detection**:
- Only loads jobs for NEW combinations (not already covered)
- If user changes "Berlin" → "Munich": only fetches Munich jobs
- If user adds "DevOps" keyword: fetches DevOps jobs for ALL locations
- If both change: fetches all new cross-products

**Example**:
```python
# User had: ['Python', 'Java'] × ['Berlin']
# User updates to: ['Python', 'Java', 'Go'] × ['Berlin', 'Munich']

# System detects:
# - New keyword: 'Go'
# - New location: 'Munich'

# Fetches:
# - 'Go' × ['Berlin', 'Munich']  # New keyword with all locations
# - ['Python', 'Java'] × ['Munich']  # Old keywords with new location
```

---

## 3. Implementation Details

### Module: `src/utils/job_loader.py`

#### Key Functions

**`load_jobs_for_combinations(keywords, locations, job_db, days_since_posted=30, background=True)`**
- Main worker function
- Fetches jobs for all keyword×location pairs
- Runs in background thread by default
- Returns statistics if background=False

**`trigger_new_user_job_load(user_id, keywords, locations, job_db)`**
- Called after user registration
- Uses default keywords/locations from config
- Non-blocking (runs in background)

**`trigger_preferences_update_job_load(user_id, old_keywords, old_locations, new_keywords, new_locations, job_db)`**
- Called when preferences are updated
- Intelligently detects NEW combinations only
- Avoids re-fetching existing combinations

**`get_default_preferences(config_path='config.yaml')`**
- Helper to load defaults from config file
- Returns dict with 'keywords' and 'locations'

### Background Processing

All job loading happens in **daemon threads**:
- ✅ Non-blocking - user doesn't wait
- ✅ Continues even if user logs out
- ✅ Multiple loads can run concurrently
- ⚠️ If server restarts mid-load, incomplete

**Daemon Thread Example**:
```python
thread = threading.Thread(
    target=_load_jobs_sync,
    args=(keywords, locations, job_db, 30),
    daemon=True
)
thread.start()
# Returns immediately - loading continues in background
```

### API Configuration

**Arbeitsagentur API**:
- Endpoint: `https://rest.arbeitsagentur.de/jobboerse/jobsuche-service`
- API Key: `jobboerse-jobsuche` (public, no registration)
- Rate Limit: None documented (we use 0.5s courtesy delay)
- Max Results: 100 per request
- Date Filter: `days_since_posted` parameter

**Safe Date Values**:
- ✅ Safe: 0, 1, 7, 14, 30
- ⚠️ Buggy: 2-6, 10, 31+
- System auto-maps to nearest safe value

---

## 4. Database Impact

### Jobs Table

**New Jobs Added**:
- Each combination can add 0-100 jobs
- Deduplication via `job_id` unique constraint
- Jobs from multiple sources (Arbeitsagentur, JSearch, etc.) coexist

**Storage Requirements**:
- Average job: ~5-10 KB
- 10,000 jobs: ~50-100 MB
- Indexes: ~10-20% overhead

### Performance

**Bulk Loader**:
- 48 combinations × 2s = ~96s total
- Database writes: ~4000 inserts
- Memory: <100 MB during load

**Trigger Loads**:
- New user (15 keywords × 3 locations): ~90s
- Preference update (5 new combos): ~10s
- Runs in background - user unaffected

---

## 5. Configuration

### `config.yaml` Defaults

Used for new users and bulk loader fallback:

```yaml
search_config:
  keywords:
    - Data Scientist
    - Machine Learning Engineer
    - AI Researcher
    - Senior Data Analyst
    - ML Ops Engineer
    # ... more keywords

  locations:
    - Berlin
    - Munich
    - Hamburg
```

### User Preferences

Stored in `users` table, `preferences` JSON column:

```json
{
  "search_keywords": [
    "Data Scientist",
    "ML Engineer"
  ],
  "search_locations": [
    "Berlin",
    "Munich"
  ]
}
```

---

## 6. Monitoring & Logs

### Log Output

**Bulk Loader**:
- Stdout console output
- Real-time progress
- Summary statistics

**Automatic Triggers**:
- Application logs (configured logger)
- Check `app.log` or stdout

**Log Level**: INFO

**Example Log Entry**:
```
INFO:src.utils.job_loader:Triggering job load for new user 42
INFO:src.utils.job_loader:Loading jobs for 15 keywords × 3 locations
INFO:src.utils.job_loader:Fetching: Data Scientist in Berlin
INFO:src.utils.job_loader:Stored 98/100 jobs for Data Scientist in Berlin
INFO:src.utils.job_loader:Job loading complete: {'total_searched': 45, 'total_fetched': 4234, 'total_stored': 4156, 'failed': 2}
```

### Flash Messages to User

**New Registration**:
- "Registration successful! Please log in."
- "Loading initial jobs in the background..."

**Preferences Update**:
- "Search preferences updated! X keywords and Y locations saved."
- "Loading jobs for new search combinations in the background..."

---

## 7. Troubleshooting

### "No user combinations found"

**Cause**: No active users or all users have empty preferences

**Solution**:
```bash
# Check users in database
sqlite3 database.db "SELECT id, email, preferences FROM users;"

# Or PostgreSQL
psql $DATABASE_URL -c "SELECT id, email, preferences FROM users;"
```

### "Jobs not appearing"

**Cause**: Background thread error or API failure

**Solution**:
1. Check logs for errors
2. Run bulk loader with verbose output
3. Test Arbeitsagentur collector directly:
   ```python
   from src.collectors.arbeitsagentur import ArbeitsagenturCollector
   collector = ArbeitsagenturCollector()
   result = collector.search_jobs(
       keywords="Data Scientist",
       location="Berlin",
       days_since_posted=7
   )
   print(result)
   ```

### "Too many duplicate jobs"

**Cause**: Multiple users with overlapping preferences

**Solution**: This is expected behavior
- Database unique constraints prevent duplicates
- Each job stored only once
- Multiple users can match the same job

### "Slow performance"

**Cause**: Large number of combinations or slow API

**Solution**:
1. Reduce default keywords in config.yaml
2. Limit locations to major cities
3. Run bulk loader during off-peak hours
4. Increase rate limiting delay

---

## 8. Best Practices

### When to Run Bulk Loader

✅ **Do**:
- Initial setup of new instance
- After importing multiple users
- Weekly/monthly refresh for comprehensive coverage
- When default config.yaml changes significantly

❌ **Don't**:
- Daily (use scheduled daily_job_updater.py instead)
- While users are actively using system
- Multiple times in quick succession

### Optimizing for Performance

1. **Limit Combinations**:
   - Use 5-10 keywords (not 50)
   - Use 2-5 locations (not all German cities)
   - Quality > quantity

2. **Staged Rollout**:
   - Start with small keyword/location set
   - Monitor job quality and relevance
   - Expand gradually

3. **Database Maintenance**:
   - Regular VACUUM (SQLite) or VACUUM ANALYZE (PostgreSQL)
   - Index on `job_id`, `source`, `discovered_date`
   - Archive old jobs (>90 days)

---

## 9. Integration with Matching

### How Loaded Jobs Are Used

1. **Job Matching Flow**:
   ```
   User clicks "Run Matching"
     ↓
   System fetches unfiltered jobs (including Arbeitsagentur jobs)
     ↓
   Semantic similarity filtering (CV vs job)
     ↓
   Claude analysis (top matches)
     ↓
   User sees matched jobs
   ```

2. **Database Query**:
   ```sql
   -- Get unfiltered jobs for user
   SELECT j.* FROM jobs j
   LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = ?
   WHERE ujm.id IS NULL AND j.status != 'deleted'
   ORDER BY j.discovered_date DESC
   ```

3. **Benefits**:
   - Larger job pool = better matches
   - Free data = lower costs vs API-only
   - Official source = high quality

---

## 10. Future Enhancements

### Planned Features

1. **Incremental Updates**:
   - Track last fetch time per combination
   - Only fetch jobs newer than last fetch
   - Reduce redundant API calls

2. **Smart Scheduling**:
   - Cron job to run bulk loader weekly
   - Stagger loads across off-peak hours
   - Priority queuing for new users

3. **User Controls**:
   - "Refresh Jobs" button in UI
   - Progress indicator for background loads
   - Notification when load completes

4. **Analytics**:
   - Track jobs loaded per source
   - Quality metrics (match rate by source)
   - Cost analysis (API vs free sources)

---

## Summary

✅ **Bulk Loader**: `python scripts/bulk_load_arbeitsagentur.py`
✅ **New User Trigger**: Automatic on registration
✅ **Preference Update Trigger**: Automatic on save
✅ **Source**: Arbeitsagentur (FREE, 150k+ jobs)
✅ **Background Processing**: Non-blocking, daemon threads
✅ **Smart Detection**: Only fetches NEW combinations

**Result**: Continuously growing job database with minimal manual effort!

---

*Last Updated: 2025-12-25*
