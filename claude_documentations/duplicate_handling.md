# Duplicate Handling Strategy

This document explains how the job-monitor system handles duplicate jobs across multiple sources.

---

## Current Implementation

### 1. **Primary Key-Based Deduplication** ✅

**Database Constraint:**
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,  -- ← UNIQUE constraint prevents exact duplicates
    ...
)
```

**How it works:**
- Each job source prefixes their external IDs with a source identifier
- Database UNIQUE constraint on `job_id` prevents duplicate inserts
- `add_job()` catches `IntegrityError` and returns `None` for duplicates

**Job ID Formats by Source:**
```
JSearch:         "<original_job_id>"              (no prefix, uses raw API ID)
Arbeitsagentur:  "arbeitsagentur_<hashId>"
Indeed:          "indeed_<job_key>"
Active Jobs:     "<original_id>"                  (no prefix)
Adzuna:          "<original_id>"                  (no prefix)
```

### 2. **Deduplication Flow**

```python
# In matcher.py - Progressive fetching
def fetch_batch_jsearch(batch_keywords, location, batch_idx):
    jobs = jsearch.search_jobs(...)
    
    new_jobs = 0
    for job in jobs:
        if job_db_inst.add_job(job):  # Returns None if duplicate
            new_jobs += 1
    
    return new_jobs  # Only counts actually inserted jobs
```

**Result:**
- Duplicate jobs are silently skipped
- Counter only increments for new jobs
- No error logs for expected duplicates

---

## Current Status (Database Analysis)

**✅ What's Working:**
- **2,267 total jobs** from 39 different sources
- **0 duplicate job_ids** (UNIQUE constraint working perfectly)
- Within each source: perfect deduplication

**⚠️ Cross-Source Duplicates Detected:**
- Same job posted on multiple ATS platforms (e.g., Greenhouse + PhenomPeople)
- 8 jobs found with identical title+company from different sources
- Examples:
  - HelloFresh jobs appear in both Greenhouse and PhenomPeople
  - Bass Pro Shops jobs in both PhenomPeople and Workday
  - Gartner job in both Workday and JSearch

---

## The Problem: Cross-Source Duplicates

### Why They Occur

1. **Companies use multiple ATS platforms**
   - Large companies post same job to Greenhouse, Workday, PhenomPeople, etc.
   - Each ATS assigns different job ID
   - Our system treats them as separate jobs

2. **Job boards syndicate content**
   - JSearch aggregates from LinkedIn, Indeed, Google Jobs
   - Active Jobs scrapes company career pages
   - Arbeitsagentur has direct postings
   - Same job appears with different IDs

3. **Current ID Strategy Preserves Source Identity**
   - `arbeitsagentur_ABC123` vs `jsearch_XYZ789`
   - Same job, different IDs → both saved to database

### Impact

**User Experience:**
- User sees same job multiple times in their matches
- Duplicate Claude analyses (wasted API credits)
- Confusing match scores (same job, different scores)

**Example from Database:**
```
Job: "Senior Backend Engineer, Data (m,f,x)" at HelloFresh
- Source 1: Active Jobs DB (greenhouse) - ID: greenhouse_12345
- Source 2: Active Jobs DB (phenompeople) - ID: phenompeople_67890
→ User sees 2 separate jobs, but it's the same position
```

---

## Solution Options

### Option 1: **Content-Based Deduplication** (Recommended)

**Strategy:** Generate a fingerprint hash from job content

**Implementation:**
```python
import hashlib

def generate_job_fingerprint(job_data):
    """Create unique fingerprint from job content"""
    # Normalize text for comparison
    title = job_data.get('title', '').lower().strip()
    company = job_data.get('company', '').lower().strip()
    location = (job_data.get('location') or '').lower().strip()
    
    # Some jobs have slight title variations, so we use first 100 chars of description
    description = (job_data.get('description') or '')[:100].lower().strip()
    
    # Create fingerprint
    fingerprint_text = f"{title}|{company}|{location}|{description}"
    fingerprint = hashlib.md5(fingerprint_text.encode()).hexdigest()
    
    return fingerprint

# In add_job()
def add_job(self, job_data: Dict[str, Any]) -> Optional[int]:
    # Generate fingerprint
    fingerprint = generate_job_fingerprint(job_data)
    
    # Check if fingerprint exists
    cursor.execute("SELECT id, source FROM jobs WHERE content_fingerprint = %s", (fingerprint,))
    existing = cursor.fetchone()
    
    if existing:
        logger.debug(f"Duplicate detected: {job_data['title']} from {job_data['source']} "
                    f"already exists from {existing[1]}")
        return None  # Skip duplicate
    
    # Insert with fingerprint
    cursor.execute("""
        INSERT INTO jobs (job_id, source, title, company, ..., content_fingerprint)
        VALUES (%s, %s, %s, %s, ..., %s)
    """, (..., fingerprint))
```

**Database Change:**
```sql
ALTER TABLE jobs ADD COLUMN content_fingerprint TEXT;
CREATE INDEX idx_jobs_fingerprint ON jobs(content_fingerprint);
```

**Pros:**
- ✅ Catches duplicates across all sources
- ✅ Works even when job IDs differ
- ✅ Fast lookup with index
- ✅ Keeps first version, skips later duplicates

**Cons:**
- ⚠️ Slight title variations might create false negatives
- ⚠️ Requires database migration
- ⚠️ Need to handle edge cases (no description, etc.)

---

### Option 2: **URL-Based Deduplication**

**Strategy:** Use job application URL as unique identifier

**Implementation:**
```python
def add_job(self, job_data: Dict[str, Any]) -> Optional[int]:
    url = job_data.get('url')
    
    if url:
        # Normalize URL (remove tracking params, etc.)
        normalized_url = normalize_url(url)
        
        # Check if URL exists
        cursor.execute("SELECT id FROM jobs WHERE normalized_url = %s", (normalized_url,))
        if cursor.fetchone():
            return None
    
    # Insert...
```

**Pros:**
- ✅ Very accurate - same URL = same job
- ✅ Simpler than content fingerprint
- ✅ Fast with index

**Cons:**
- ⚠️ Not all jobs have URLs
- ⚠️ Some platforms use redirects/tracking links (same job, different URLs)
- ⚠️ URL might change while job is still active

---

### Option 3: **Smart Merging** (Advanced)

**Strategy:** Keep duplicates but mark them as related, merge data

**Implementation:**
```python
# When duplicate detected
def add_job(self, job_data: Dict[str, Any]) -> Optional[int]:
    fingerprint = generate_job_fingerprint(job_data)
    
    cursor.execute("SELECT id FROM jobs WHERE content_fingerprint = %s", (fingerprint,))
    existing_id = cursor.fetchone()
    
    if existing_id:
        # Create duplicate relationship
        cursor.execute("""
            INSERT INTO job_duplicates (primary_job_id, duplicate_job_id, source)
            VALUES (%s, %s, %s)
        """, (existing_id[0], job_data['job_id'], job_data['source']))
        
        # Update existing job with additional sources
        cursor.execute("""
            UPDATE jobs
            SET sources = array_append(sources, %s)
            WHERE id = %s
        """, (job_data['source'], existing_id[0]))
        
        return existing_id[0]  # Return existing job ID
```

**Pros:**
- ✅ Preserves all source information
- ✅ User sees one job with multiple application options
- ✅ Can track which sources are most reliable

**Cons:**
- ⚠️ Complex implementation
- ⚠️ Need to handle UI changes (show multiple sources)
- ⚠️ More database complexity

---

## Recommended Approach

**Phase 1: Content Fingerprint (Quick Win)**
1. Add `content_fingerprint` column to jobs table
2. Generate fingerprint from: title + company + location + first 100 chars of description
3. Check fingerprint before insert, skip if exists
4. Add index for fast lookups

**Phase 2: Enhanced Deduplication (Future)**
1. Track which source was seen first (priority: Arbeitsagentur > JSearch > Active Jobs)
2. Store alternate sources in JSON array
3. Update UI to show "Available on 3 platforms" with links

**Phase 3: User Feedback (Optional)**
1. Add "Mark as duplicate" button
2. Learn from user feedback to improve fingerprinting
3. Adjust fingerprint algorithm based on false positives/negatives

---

## Implementation Code

### Migration Script

```python
# scripts/add_fingerprint_deduplication.py
import hashlib
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def generate_fingerprint(title, company, location, description):
    """Generate content fingerprint"""
    title = (title or '').lower().strip()
    company = (company or '').lower().strip()
    location = (location or '').lower().strip()
    desc = (description or '')[:100].lower().strip()
    
    text = f"{title}|{company}|{location}|{desc}"
    return hashlib.md5(text.encode()).hexdigest()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Add column
cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS content_fingerprint TEXT")

# Generate fingerprints for existing jobs
cur.execute("SELECT id, title, company, location, description FROM jobs")
for job_id, title, company, location, description in cur.fetchall():
    fingerprint = generate_fingerprint(title, company, location, description)
    cur.execute("UPDATE jobs SET content_fingerprint = %s WHERE id = %s", (fingerprint, job_id))

# Create index
cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(content_fingerprint)")

conn.commit()
print("✅ Fingerprint deduplication enabled")
```

### Updated add_job() Method

```python
def add_job(self, job_data: Dict[str, Any]) -> Optional[int]:
    """Add job with content-based deduplication"""
    try:
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(
            job_data.get('title'),
            job_data.get('company'),
            job_data.get('location'),
            job_data.get('description')
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check for duplicate fingerprint
        cursor.execute(
            "SELECT id, source FROM jobs WHERE content_fingerprint = %s",
            (fingerprint,)
        )
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"Duplicate skipped: '{job_data['title']}' from {job_data['source']} "
                       f"(already exists from {existing[1]})")
            return None
        
        # Insert with fingerprint
        cursor.execute("""
            INSERT INTO jobs (
                job_id, source, title, company, location, description,
                url, posted_date, salary, discovered_date, last_updated,
                content_fingerprint, priority, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            job_data.get('job_id') or job_data.get('external_id'),
            job_data.get('source'),
            job_data.get('title'),
            job_data.get('company'),
            job_data.get('location'),
            job_data.get('description'),
            job_data.get('url'),
            posted_date,
            job_data.get('salary'),
            now,
            now,
            fingerprint,  # ← New field
            job_data.get('priority', 'medium'),
            'new'
        ))
        
        job_id = cursor.fetchone()[0]
        conn.commit()
        return job_id
        
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
    finally:
        cursor.close()
        self._return_connection(conn)

def _generate_fingerprint(self, title, company, location, description):
    """Generate content fingerprint for deduplication"""
    import hashlib
    
    title = (title or '').lower().strip()
    company = (company or '').lower().strip()
    location = (location or '').lower().strip()
    desc = (description or '')[:100].lower().strip()
    
    text = f"{title}|{company}|{location}|{desc}"
    return hashlib.md5(text.encode()).hexdigest()
```

---

## Testing Strategy

1. **Unit Tests:**
   - Test fingerprint generation with same content
   - Test with slight variations (punctuation, case)
   - Test with missing fields

2. **Integration Test:**
   - Insert same job from 2 sources
   - Verify only 1 saved
   - Verify second returns None

3. **Database Analysis:**
   - After deployment, check for remaining duplicates
   - Monitor fingerprint collision rate
   - Adjust algorithm if needed

---

## Decision Required

**Question:** Should we implement content-based deduplication to prevent cross-source duplicates?

**Current State:**
- 8 known cross-source duplicates in database (out of 2,267 jobs)
- Users may see same job 2-3 times from different sources
- Wasting Claude API credits analyzing duplicates

**Impact:**
- **Low priority**: Only 0.35% duplicate rate currently
- **Medium impact**: Better user experience, cost savings
- **Low risk**: Can be implemented incrementally

**Recommendation:** 
- **Yes**, implement in next sprint
- Start with Option 1 (Content Fingerprint)
- Monitor for 1 week, adjust algorithm if needed
- Consider Option 3 (Smart Merging) for Phase 2

---

**Last Updated:** 2025-12-25
