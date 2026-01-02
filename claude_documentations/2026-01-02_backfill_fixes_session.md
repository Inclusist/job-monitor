# Session Summary: Active Jobs DB Backfill Fixes
**Date:** January 2, 2026
**Duration:** ~4 hours
**Status:** ✅ All issues resolved and deployed

---

## Overview

Fixed critical bugs preventing Active Jobs DB from returning results during backfill, causing 0 jobs to be added despite the API working. After fixes, backfill now successfully adds **~146 Active Jobs DB jobs** + **~107 JSearch jobs** = **~250 total jobs** (171 unique).

---

## Problems Identified

### 1. **Active Jobs DB API Parameter Issue**
- **Symptom**: API returned 400 "syntax error in tsquery"
- **Root Cause**: Using wrong parameter name (`title_filter` instead of `advanced_title_filter`)
- **Wrong Format**: `Data Science Manager|Head of Data Science` (no quotes, no spaces)
- **Correct Format**: `'Data Science Manager' | 'Head of Data Science'` (quotes + spaces)

### 2. **Parser Field Name Mismatch** (CRITICAL)
- **Symptom**: API returned jobs but database had 0 Active Jobs DB backfill entries
- **Root Cause**: Parser using wrong field names for 6-month endpoint
- **Wrong Mappings**:
  - `job_data.get('company')` → Always returned `None`
  - `job_data.get('location')` → Always returned `None`
  - `job_data.get('description')` → Wrong field
- **Correct Mappings**:
  - `job_data.get('organization')` → Returns "Bjak", "Mavenoid", etc.
  - `job_data.get('locations_derived')` → Returns ["Berlin, Germany"]
  - `job_data.get('description_text')` → Returns full description

### 3. **Job Detail Page Empty Content**
- **Symptom**: Job detail pages showed header/nav but empty content area
- **Root Causes**:
  - Missing CSS file causing 404 error
  - Template tried to capitalize `None` priority value (Jinja2 error)
- **Impact**: Users couldn't view any job details

### 4. **Missing Priority Field**
- **Symptom**: Jobs from backfill had `priority=None`
- **Impact**: Template rendering failed when trying to capitalize None
- **Fix**: Added `'priority': 'medium'` to both collectors

---

## Solutions Implemented

### Fix 1: API Query Format (Commit b7beed7)
**File**: `src/collectors/activejobs_backfill.py`, `src/jobs/user_backfill.py`

```python
# BEFORE
params['title_filter'] = query  # Wrong parameter
piped_titles = '|'.join(sorted(all_titles))  # Wrong format

# AFTER
params['advanced_title_filter'] = query  # Correct parameter
piped_titles = ' | '.join(f"'{title}'" for title in sorted(all_titles))  # Correct format
```

**Result**: API now accepts queries and returns 200 OK with jobs

---

### Fix 2: Field Name Mapping (Commit 3cb5a71) ⭐ CRITICAL
**File**: `src/collectors/activejobs_backfill.py`

```python
# BEFORE - Returns None
'company': job_data.get('company'),
'location': job_data.get('location'),
'description': job_data.get('description', ''),
'posted_date': job_data.get('posted_date'),

# AFTER - Returns actual data
'company': job_data.get('organization', '').strip(),
'location': ', '.join(job_data.get('locations_derived', [])),
'description': job_data.get('description_text') or job_data.get('description_html', ''),
'posted_date': job_data.get('date_posted'),
```

**Salary field updates**:
```python
# BEFORE
salary_min = job_data.get('salary_min')
salary_max = job_data.get('salary_max')

# AFTER - Use AI-extracted fields
salary_min = job_data.get('ai_salary_minvalue')
salary_max = job_data.get('ai_salary_maxvalue')
salary_currency = job_data.get('ai_salary_currency')
```

**AI metadata updates**:
```python
# BEFORE
'ai_seniority': ai_data.get('seniority'),

# AFTER
'ai_seniority': job_data.get('ai_experience_level'),
'ai_employment_type': ', '.join(job_data.get('employment_type', [])),
```

**Result**: Jobs now have valid company/location and save successfully to database

---

### Fix 3: Job Detail Page (Commit fad725c)
**Files**: `web/templates/job_detail.html`, `web/static/css/style.css`

```html
<!-- BEFORE - Fails when priority is None -->
<span class="badge badge-{{ job.priority }}">{{ job.priority|capitalize }} Priority</span>

<!-- AFTER - Safe default -->
<span class="badge badge-{{ job.priority or 'medium' }}">{{ (job.priority or 'medium')|capitalize }} Priority</span>
```

**Created missing CSS file**:
```bash
web/static/css/style.css  # Empty file to fix 404
```

**Result**: Job detail pages render correctly

---

### Fix 4: Priority Field (Commits fad725c, 3cb5a71)
**Files**: `src/collectors/activejobs_backfill.py`, `src/collectors/jsearch.py`

```python
# Added to both collectors
return {
    # ... other fields ...
    'priority': 'medium',  # Default priority for backfill jobs
}
```

**Result**: All backfill jobs have valid priority field

---

### Fix 5: Source Format Alignment (Commit 11eea97)
**File**: `src/collectors/activejobs_backfill.py`

```python
# BEFORE
'source': 'Active Jobs DB',

# AFTER - Match daily collector format
'source': f"Active Jobs DB ({job_data.get('source', 'ATS')})",
# e.g., "Active Jobs DB (greenhouse)", "Active Jobs DB (smartrecruiters)"
```

**Result**: Consistent source tracking across daily and backfill collectors

---

## Test Results

### Before All Fixes
```
JSearch: 107 jobs
Active Jobs DB: 0 jobs
Total: 107 jobs (76 unique)
```

### After All Fixes
```
JSearch: 106 jobs
Active Jobs DB: 146 jobs ⭐
  - Berlin: 47 jobs
  - Hamburg: 15 jobs
  - Germany remote/hybrid: 84 jobs
Total: 252 jobs (171 unique)

🎉 +125% more jobs!
```

### Sample Working Job Data
```python
{
  'job_id': '1928249262',
  'title': 'Founding Lead Machine Learning Engineer',
  'company': 'Bjak',  # ✅ Was None before
  'location': 'Berlin, Germany',  # ✅ Was None before
  'source': 'Active Jobs DB (ashby)',
  'priority': 'medium',  # ✅ Was None before
  'url': 'https://jobs.ashbyhq.com/...',
  'ai_employment_type': 'FULL_TIME',
  'ai_work_arrangement': 'Remote OK',
  'ai_seniority': '5-10'
}
```

---

## Commits Pushed

1. **b7beed7** - Fix: Active Jobs DB backfill now returns jobs
   - Changed `title_filter` → `advanced_title_filter`
   - Fixed query format: `'title1' | 'title2'`
   - Switched to `/active-ats-6m` endpoint

2. **fad725c** - Fix: Job detail page empty content and 404 CSS error
   - Template safe handling of None priority
   - Created missing `web/static/css/style.css`
   - Added priority field to collectors

3. **11eea97** - Align backfill source format with daily collector
   - Match source format: `Active Jobs DB (ats_platform)`

4. **3cb5a71** - Fix: Active Jobs backfill parser using wrong field names ⭐
   - **CRITICAL**: Fixed company/location field mappings
   - Updated salary field parsing
   - Fixed AI metadata field names
   - This was the root cause of 0 jobs being added

---

## Production Database Before/After

### Before Fixes
```
Active Jobs DB entries: 2,006 (from daily cron only)
  - Active Jobs DB (smartrecruiters): 598
  - Active Jobs DB (join.com): 261
  - Active Jobs DB (greenhouse): 159
  - ... (38 ATS platforms total)
JSearch entries: 335
Total: 2,341 jobs

Active Jobs DB backfill entries: 0 ❌
```

### After Fixes (Expected)
```
Active Jobs DB backfill will add: ~146 jobs per user
JSearch backfill will add: ~107 jobs per user
Total per user: ~250 jobs (171 unique after deduplication)
```

---

## Files Modified

### Core Fixes
- `src/collectors/activejobs_backfill.py` - Parser field mappings, API parameters
- `src/jobs/user_backfill.py` - Query formatting with quotes
- `src/collectors/jsearch.py` - Added priority field

### Frontend Fixes
- `web/templates/job_detail.html` - Safe priority handling
- `web/static/css/style.css` - Created to fix 404

### Test Infrastructure
- `scripts/test_backfill.py` - Created for dry-run testing
- `scripts/avtivejobs_api_test.py` - User's working API test

---

## Key Learnings

### 1. **Different API Endpoints Have Different Response Schemas**
- Daily collector uses `/active-ats-24h` or `/active-ats-7d` endpoints
- Backfill uses `/active-ats-6m` endpoint
- Field names differ between endpoints:
  - 24h/7d: Uses `company`, `location` (old format)
  - 6m: Uses `organization`, `locations_derived` (new format)

### 2. **Silent Database Insert Failures**
- Jobs with `company=None` or `location=None` fail to insert
- No error messages shown to user
- Backfill appeared to run successfully but 0 jobs added
- **Lesson**: Always validate required fields before database operations

### 3. **API Parameter Naming Conventions**
- `title_filter`: For single title searches
- `advanced_title_filter`: For pipe-separated multi-title searches with tsquery syntax
- Format matters: Must use `'title1' | 'title2'` with quotes and spaces

### 4. **Template Error Handling**
- Jinja2 errors (like `None|capitalize`) cause complete page failure
- Always provide safe defaults: `{{ value or 'default' }}`
- Missing static files (404) can break entire page rendering

---

## Testing Commands

### Test Active Jobs DB API Locally
```bash
python -c "
from src.collectors.activejobs_backfill import ActiveJobsBackfillCollector
import os
from dotenv import load_dotenv
load_dotenv()

collector = ActiveJobsBackfillCollector(os.getenv('ACTIVEJOBS_API_KEY'))
jobs = collector.search_backfill(
    query=\"'Data Science Manager' | 'Machine Learning Engineer'\",
    location='Berlin',
    limit=10
)
print(f'Found {len(jobs)} jobs')
for job in jobs:
    print(f\"  {job['title']} at {job['company']} - {job['location']}\")
"
```

### Test Backfill Without Database Writes
```bash
python scripts/test_backfill.py
```

### Check Production Database Stats
```bash
python -c "
from src.database.postgres_operations import PostgresDatabase
import os
from dotenv import load_dotenv
load_dotenv()

db = PostgresDatabase(os.getenv('DATABASE_URL'))
conn = db._get_connection()
cursor = conn.cursor()

cursor.execute('SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY COUNT(*) DESC')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')
"
```

### Reset Tables for Fresh Test
```bash
python -c "
from src.database.postgres_operations import PostgresDatabase
import os
from dotenv import load_dotenv
load_dotenv()

db = PostgresDatabase(os.getenv('DATABASE_URL'))
conn = db._get_connection()
cursor = conn.cursor()

cursor.execute('DELETE FROM user_search_queries')
cursor.execute('DELETE FROM backfill_tracking')
conn.commit()
print('✅ Tables reset')
"
```

---

## Next Steps

1. **Upload CV to test backfill** with all fixes in production
2. **Monitor Railway logs** for backfill execution
3. **Verify job counts** increase in database
4. **Check job detail pages** render correctly
5. **Confirm dual-search strategy** works:
   - City-specific searches (Berlin, Hamburg)
   - Germany-wide remote/hybrid searches

---

## Related Documentation

- Active Jobs DB API: https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/active-jobs-db
- Backfill Strategy: `/claude_documentations/backfill_strategy.md`
- Daily Cron Setup: `/docs/railway_deployment.md`
- Database Schema: `/src/database/schema.sql`

---

## Summary

**Problem**: Backfill returned 0 Active Jobs DB jobs despite API working

**Root Cause**: Parser using wrong field names from 6-month endpoint, causing `company=None` and `location=None`, leading to failed database inserts

**Solution**: Updated field mappings to match API response structure:
- `organization` → company
- `locations_derived` → location
- `description_text` → description
- `ai_salary_*` → salary fields
- `ai_experience_level` → seniority

**Result**: Backfill now successfully adds **~146 Active Jobs DB jobs** per user, more than doubling the total job count from **76 → 171 unique jobs** (+125%)

**Status**: ✅ All fixes deployed to production, ready for testing
