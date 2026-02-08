# Job Display & Matching Bugs - Investigation & Fix Plan

**Date:** January 2, 2026
**Status:** 🔴 Investigation Phase
**Priority:** High

---

## Bugs Reported

### Bug 1: Priority Mismatch Between List and Detail Views

**Symptoms:**
- Job search/list page shows: `Priority: High`
- Job detail page shows: `Priority: Medium`
- Same job displays different priorities in different views

**User Impact:**
- Confusing and misleading
- Users can't trust the priority indicators
- Undermines the matching/scoring system

**Investigation Needed:**
1. Check where priority comes from in jobs list vs detail page
2. Verify if it's coming from different tables:
   - `jobs.priority` (global)
   - `user_job_matches.priority` (user-specific)
3. Determine which one should be the source of truth

**Hypothesis:**
- List page might show `jobs.priority` (set by collector = 'medium')
- Detail page might show `user_job_matches.priority` (set by Claude matching)
- OR vice versa - need to check code

---

### Bug 2: Missing Match Reasoning ("No reasoning provided")

**Symptoms:**
- Match Analysis section on job detail page shows: "No reasoning provided"
- No explanation of why job matches user's profile
- Missing key alignments and potential gaps

**User Impact:**
- Users don't understand why jobs are recommended
- Can't make informed decisions
- Defeats purpose of AI-powered matching

**Investigation Needed:**
1. Check if Claude analysis is running at all
2. Verify if `match_reasoning` field is being populated
3. Check if it's stored in:
   - `jobs.match_reasoning` (global)
   - `user_job_matches.match_reasoning` (user-specific)
4. Review Claude scoring workflow
5. Check logs for Claude API errors

**Hypothesis:**
- Claude matching might not be triggered for backfill jobs
- Only semantic matching is running (gives scores but no reasoning)
- Reasoning might be in `user_job_matches` but detail page reads from `jobs` table

**Related Code:**
- Job matching: `src/jobs/job_matcher.py` (if exists)
- Route: `app.py` line 910-942 (`job_detail()`)
- Template: `web/templates/job_detail.html` line 133-138

---

### Bug 3: Duplicate Jobs with Location Format Variations

**Symptoms:**

**Example 1:**
- Job A: "Data Science Manager (w/m/d)" at "Billie" - Location: "Berlin, Germany" - Score: 88
- Job B: "Data Science Manager (w/m/d)" at "Billie" - Location: "Berlin" - Score: 88
- **Same job, different location format**

**Example 2:**
- Job A: "Team Lead Data Science (f/m/x)" at "AUTO1 Group" - Location: "Berlin" - Score: 88
- Job B: "Team Lead Data Science (f/m/x)" at "AUTO1 Group" - Location: "Berlin, Germany" - Score: 85
- **Same job, different location format and score**

**User Impact:**
- Cluttered job list
- Wasted API quota (counting same job twice)
- Confusing user experience
- Users might apply to same job twice

**Root Cause Analysis:**

**Likely causes:**
1. **Different API sources with different location formats:**
   - JSearch returns: "Berlin"
   - Active Jobs DB returns: "Berlin, Germany"

2. **Location normalization missing:**
   - Deduplication uses `external_id` or `url` as key
   - But same job from different sources might have different IDs
   - Location format differs but represents same job

3. **Multiple postings by same company:**
   - Company might post same job on multiple platforms
   - Each platform assigns different ID
   - Our system sees them as different jobs

**Investigation Needed:**
1. Check how deduplication works currently
2. Verify `external_id` generation for each source
3. Check if jobs have same URL despite different sources
4. Review location normalization logic
5. Check if these are truly duplicates or separate postings

**Deduplication Strategy Options:**

**Option A: Normalize location before deduplication**
```python
def normalize_location(location):
    # Remove country suffix if present
    # "Berlin, Germany" -> "Berlin"
    # "Hamburg, Germany" -> "Hamburg"
    if location:
        location = location.strip()
        # Remove ", Germany" suffix
        if location.endswith(', Germany'):
            location = location[:-10]
    return location
```

**Option B: Compound deduplication key**
```python
dedup_key = (
    normalize_title(job['title']),
    job['company'].lower().strip(),
    normalize_location(job['location']),
    job.get('posted_date')  # Same date = likely same posting
)
```

**Option C: Fuzzy matching for duplicates**
- Use title + company + location similarity
- Consider jobs duplicates if:
  - Same company (exact match)
  - Same or very similar title (Levenshtein distance < 3)
  - Same city (normalized location)
  - Posted within 7 days of each other

---

## Investigation Plan

### Phase 1: Data Collection (15 min)

**Check production database:**
```python
# Get sample job with high priority from list
SELECT j.id, j.title, j.company, j.priority as job_priority,
       ujm.priority as user_priority, ujm.match_reasoning,
       j.match_reasoning as job_reasoning
FROM jobs j
LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = 1
WHERE j.title LIKE '%Data Science Manager%'
AND j.company = 'Billie'
LIMIT 5;
```

**Check for duplicates:**
```python
# Find potential duplicates (same company + similar title + different location)
SELECT
    title, company, location, url, source,
    COUNT(*) as count,
    STRING_AGG(CAST(id AS TEXT), ', ') as job_ids
FROM jobs
WHERE company IN ('Billie', 'AUTO1 Group')
GROUP BY title, company, location, url, source
HAVING COUNT(*) > 1;
```

**Check reasoning population:**
```python
# How many jobs have reasoning?
SELECT
    COUNT(*) as total_jobs,
    COUNT(match_reasoning) as jobs_with_reasoning,
    COUNT(ujm.match_reasoning) as matches_with_reasoning
FROM jobs j
LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id;
```

### Phase 2: Code Review (20 min)

**Files to check:**

1. **Priority display logic:**
   - `app.py` - `/jobs` route (job list)
   - `app.py` - `/jobs/<id>` route (job detail)
   - `web/templates/jobs.html` - list view priority source
   - `web/templates/job_detail.html` - detail view priority source

2. **Match reasoning logic:**
   - `app.py` - `job_detail()` function
   - Job matching service (where Claude scoring happens)
   - Check if reasoning is populated during matching

3. **Deduplication logic:**
   - `src/jobs/user_backfill.py` - `_deduplicate_jobs()`
   - `src/collectors/jsearch.py` - how external_id is set
   - `src/collectors/activejobs_backfill.py` - how external_id is set
   - Location normalization (if any)

### Phase 3: Root Cause Identification (15 min)

**Bug 1 - Priority:**
- [ ] Identify which table/field is used in list vs detail
- [ ] Determine if priority should be user-specific or global
- [ ] Check if priority is being overwritten somewhere

**Bug 2 - Reasoning:**
- [ ] Check if Claude matching is running for new jobs
- [ ] Verify where reasoning should be stored
- [ ] Check if reasoning is lost during user isolation fix

**Bug 3 - Duplicates:**
- [ ] Verify if jobs are truly duplicates (same URL?)
- [ ] Check if different sources assign different IDs
- [ ] Identify location normalization gaps

---

## Fix Strategy

### Bug 1: Priority Mismatch

**Preferred Solution:**
Use user-specific priority from `user_job_matches.priority` everywhere:

```python
# In job_detail() route
job = job_db.get_job_by_id(job_id)

# Get user-specific data
user_id = get_user_id()
user_job_data = job_db.get_user_job_match(user_id, job_id)

# Override with user-specific priority
if user_job_data:
    job['priority'] = user_job_data.get('priority') or job['priority']
    job['match_reasoning'] = user_job_data.get('match_reasoning') or job['match_reasoning']
    job['match_score'] = user_job_data.get('claude_score') or job['match_score']
```

**Files to modify:**
- `src/database/postgres_operations.py` - Add `get_user_job_match()` method
- `app.py` - Update `job_detail()` to merge user-specific data
- Verify `/jobs` route also uses user-specific priority

---

### Bug 2: Missing Reasoning

**Investigation Path 1: Check if Claude matching runs**

```bash
# Check logs for Claude API calls
grep -r "claude" logs/

# Check if Claude scoring is triggered
# Look for job matching service
```

**Investigation Path 2: Check data population**

```python
# Check if any jobs have reasoning
SELECT COUNT(*),
       COUNT(match_reasoning) as with_reasoning,
       COUNT(CASE WHEN match_reasoning IS NOT NULL AND match_reasoning != '' THEN 1 END) as non_empty
FROM jobs;

# Check user_job_matches
SELECT COUNT(*),
       COUNT(match_reasoning) as with_reasoning
FROM user_job_matches;
```

**Potential Fix 1: Reasoning in wrong table**
- Detail page reads from `jobs.match_reasoning`
- But reasoning is stored in `user_job_matches.match_reasoning`
- Solution: Merge user-specific data in job_detail route

**Potential Fix 2: Claude matching not triggered**
- Check if matching service is called after job collection
- Trigger Claude matching for backfill jobs
- Update job matcher to populate reasoning field

---

### Bug 3: Duplicate Jobs

**Quick Fix (Short-term):**

Location normalization before deduplication:

```python
def normalize_location(location: str) -> str:
    """Normalize location for deduplication"""
    if not location:
        return ''

    location = location.strip()

    # Remove ", Germany" suffix
    if location.endswith(', Germany'):
        location = location[:-10].strip()

    # Remove ", DE" suffix
    if location.endswith(', DE'):
        location = location[:-4].strip()

    return location

def _deduplicate_jobs(jobs, seen_job_ids, deleted_ids):
    """Remove duplicate and deleted jobs"""
    unique_jobs = []

    for job in jobs:
        # Primary dedup key: external_id or URL
        job_id = job.get('external_id') or job.get('url', '')

        # Secondary dedup key: normalized signature
        signature = (
            job.get('title', '').lower().strip(),
            job.get('company', '').lower().strip(),
            normalize_location(job.get('location', ''))
        )

        if job_id in seen_job_ids:
            continue

        # Check if signature already seen (catches different IDs, same job)
        if signature in seen_signatures:
            continue

        seen_job_ids.add(job_id)
        seen_signatures.add(signature)
        unique_jobs.append(job)

    return unique_jobs
```

**Comprehensive Fix (Long-term):**

1. **Normalize locations in collectors:**
   - Update `activejobs_backfill.py` location parsing
   - Update `jsearch.py` location parsing
   - Ensure consistent format before storing

2. **Improve deduplication:**
   - Use compound key (title + company + normalized location)
   - Consider fuzzy matching for titles
   - Add posted_date proximity check

3. **Database constraint:**
   - Add unique index on (company, normalized_title, normalized_location, posted_date)
   - Prevents duplicates at database level

---

## Testing Plan

### Test Bug 1: Priority

```python
# 1. Create test job with priority in user_job_matches
# 2. View job in list - check priority
# 3. Click into detail view - check priority
# 4. Both should show same priority
```

### Test Bug 2: Reasoning

```python
# 1. Trigger Claude matching for a job
# 2. Verify reasoning is populated
# 3. Check job detail page shows reasoning
# 4. Verify it's user-specific (different users see different reasoning)
```

### Test Bug 3: Deduplication

```python
# Before fix: Count jobs from Billie
SELECT COUNT(*) FROM jobs WHERE company = 'Billie' AND title LIKE '%Data Science Manager%';

# Apply normalization fix

# After fix: Re-run backfill and verify count decreases
# Should see only unique jobs
```

---

## Success Criteria

### Bug 1: Priority
- ✅ Priority matches between list and detail views
- ✅ User-specific priority takes precedence
- ✅ No more confusion for users

### Bug 2: Reasoning
- ✅ Match Analysis shows meaningful reasoning
- ✅ Key alignments populated
- ✅ Potential gaps identified
- ✅ Users understand why jobs match

### Bug 3: Duplicates
- ✅ No duplicate jobs with same title + company + city
- ✅ Location variations normalized ("Berlin" vs "Berlin, Germany")
- ✅ Job list contains only unique opportunities
- ✅ Reduced clutter and better UX

---

## Priority & Timeline

**Priority Order:**
1. **Bug 2 (Reasoning)** - High Impact - Core value prop of AI matching
2. **Bug 3 (Duplicates)** - High Impact - User experience and quota waste
3. **Bug 1 (Priority)** - Medium Impact - Confusing but not blocking

**Estimated Effort:**
- Bug 1: 30 min (small code change)
- Bug 2: 1-2 hours (depends on if matching is running or not)
- Bug 3: 45 min (location normalization) OR 2-3 hours (comprehensive dedup)

---

## Files to Modify

### Bug 1: Priority
- `src/database/postgres_operations.py` - Add `get_user_job_match()`
- `app.py` - Update `job_detail()` route

### Bug 2: Reasoning
- `app.py` - Update `job_detail()` to fetch user-specific reasoning
- Check job matching service
- Potentially update matching trigger

### Bug 3: Duplicates
- `src/jobs/user_backfill.py` - Update `_deduplicate_jobs()`
- `src/collectors/activejobs_backfill.py` - Normalize location parsing
- `src/collectors/jsearch.py` - Normalize location parsing
- Create `src/utils/location_normalizer.py` (new file)

---

## Next Steps

1. **Run investigation queries** on production database
2. **Review code** in files listed above
3. **Identify root causes** for each bug
4. **Implement fixes** in priority order
5. **Test locally** before deploying
6. **Deploy to production**
7. **Verify fixes** with user

---

## Notes

- All three bugs are related to data consistency and display
- Priority fix should use user-specific data (aligns with privacy fix)
- Reasoning might be missing due to recent user isolation changes
- Duplicates waste API quota and confuse users - important to fix
