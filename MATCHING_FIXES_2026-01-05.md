# Job Matching Fixes - January 5, 2026

## Issues Found

### 1. ❌ Claude Analysis Didn't Run
**Problem:** 0 out of 1,876 matches got Claude analysis

**Root Cause:** Matching ran at 09:16 this morning with OLD code:
- Old threshold: ≥70% (only 2 jobs qualified)
- New threshold: ≥50% (169 jobs should qualify!)

**Evidence:**
```
Semantic Score Distribution:
- 70-100%: 2 jobs (old threshold)
- 50-69%: 167 jobs (NEW threshold would catch these!)
- 30-49%: 1,707 jobs
```

### 2. ❌ US Jobs from JSearch
**Problem:** 23 out of 87 JSearch jobs are from the US

**Root Cause:** JSearch API doesn't respect `country=de` parameter properly

**Evidence:**
```
JSearch Locations:
- Germany: 24 jobs
- US: 23 jobs (should be 0!)
- Other: 62 jobs
```

### 3. ✅ Active Jobs DB Jobs Are There
**Problem:** User thought Active Jobs DB jobs weren't matched

**Reality:** They're there, just with lower scores than JSearch
- Active Jobs DB matches: 78 total
- They rank lower in semantic matching
- Examples: "Active Jobs DB (join.com): 26", "Active Jobs DB (workday): 11"

---

## Fixes Applied

### Fix 1: Enhanced Claude Matching (Already Done Yesterday)
**Files Changed:**
- `src/analysis/claude_analyzer.py` - Enhanced prompt with AI metadata
- `src/matching/matcher.py` - Lowered threshold to 50%

**Status:** ✅ Code is ready, just needs re-run

### Fix 2: JSearch Country Filter (NEW)
**File Changed:** `src/collectors/jsearch.py`

**What Changed:**
Added post-filtering after API returns results:
```python
# Apply country filter if specified
if country and country == 'de':
    # Only include German jobs
    job_country = job.get("job_country", "")
    job_city = job.get("job_city", "")

    # Check if job is in Germany
    is_german = (
        job_country == "DE" or
        "Germany" in str(job_country) or
        job_city in [list of 80+ German cities]
    )

    if not is_german:
        continue  # Skip non-German jobs
```

**Status:** ✅ Fixed and ready

---

## How to Re-Run Matching with Fixes

### Step 1: Run the Re-Matching Script

```bash
cd /Users/prabhu.ramachandran/job-monitor
python scripts/rerun_matching_with_enhanced_claude.py
```

**What This Does:**
1. Clears old matches (from 09:16 run with old code)
2. Runs NEW matching with:
   - ✅ 50% Claude threshold (was 70%)
   - ✅ Enhanced Claude prompt (uses AI metadata)
   - ✅ Fixed JSearch country filter
3. Shows statistics

**Expected Results:**
- Semantic matches: ~1,800-2,000 (similar to before)
- **Claude analysis: ~150-200 jobs** (was 0!)
- Germany-only JSearch jobs
- Better match reasoning with specific skills/gaps

---

## Expected Output

```
==========================================================
RE-RUN MATCHING WITH ENHANCED CLAUDE
==========================================================

User: your@email.com
User ID: 1

Current matches: 1,876

🗑️  Clearing old matches...
   ✓ Cleared 1,876 old matches

📊 Total jobs to match against: 4,133

🚀 Starting enhanced matching...
   • Semantic threshold: ≥30%
   • Claude threshold: ≥50% (NEW - was 70%)
   • Enhanced Claude prompt with AI metadata

[Matching progress...]

==========================================================
✅ MATCHING COMPLETE!
==========================================================
Matches found: 1,950
Jobs analyzed by Claude: 180

With Claude analysis: 180
Semantic only: 1,770

Top sources with Claude analysis:
  join.com: 45
  JSearch: 28
  smartrecruiters: 25
  ...

💡 View jobs at http://localhost:5000/jobs
```

---

## What to Check After Re-Run

### 1. Claude Analysis Running
**Check:** Number of jobs with Claude analysis

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
import psycopg2, os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM user_job_matches WHERE claude_score IS NOT NULL')
print(f'Jobs with Claude: {cursor.fetchone()[0]:,}')
"
```

**Expected:** 150-200 jobs (was 0)

### 2. Match Reasoning Quality
**Check:** Job detail pages should show:
- ✅ Specific matching skills: "Python, SQL, Machine Learning"
- ✅ Specific missing skills: "AWS, Kubernetes, Docker"
- ✅ Experience comparison: "5 years vs 3-5 required"
- ❌ NOT generic: "Good alignment with your background"

### 3. JSearch Country Filter
**Check:** No more US jobs

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
import psycopg2, os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
cursor.execute(\"SELECT COUNT(*) FROM jobs WHERE source='JSearch' AND location LIKE '%US%'\")
print(f'JSearch US jobs: {cursor.fetchone()[0]}')
"
```

**Expected:** 0 US jobs from future JSearch runs

**Note:** Existing 23 US jobs will stay in database, but they won't match if semantic scores are low

### 4. Active Jobs DB in Top Matches
**Check:** After re-run, check if Active Jobs DB jobs rank higher with Claude analysis

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
import psycopg2, os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
cursor.execute('''
    SELECT j.title, j.company, ujm.claude_score, j.source
    FROM user_job_matches ujm
    JOIN jobs j ON ujm.job_id = j.id
    WHERE ujm.claude_score IS NOT NULL
    AND j.source LIKE 'Active Jobs DB%'
    ORDER BY ujm.claude_score DESC
    LIMIT 10
''')
print('Top Active Jobs DB matches with Claude:')
for row in cursor.fetchall():
    print(f'{row[2]}% - {row[0][:50]} ({row[3]})')
"
```

---

## Files Changed

### Enhanced Matching (Yesterday)
- ✅ `src/analysis/claude_analyzer.py` - Enhanced Claude prompt
- ✅ `src/matching/matcher.py` - 50% threshold

### Country Filter (Today)
- ✅ `src/collectors/jsearch.py` - Post-filter German jobs only

### New Scripts (Today)
- ✅ `scripts/rerun_matching_with_enhanced_claude.py` - Clean re-run script

---

## Summary

**Problems:**
1. Claude didn't run (old 70% threshold)
2. US jobs from JSearch (API filter not working)
3. Active Jobs jobs present but low-ranked

**Solutions:**
1. ✅ Re-run with 50% threshold + enhanced prompt
2. ✅ Added Germany-only post-filtering for JSearch
3. ✅ Claude analysis will rank jobs better with AI metadata

**Next Step:**
```bash
python scripts/rerun_matching_with_enhanced_claude.py
```

Then check results in web UI at `/jobs`!
