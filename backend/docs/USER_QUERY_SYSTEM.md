# User Query-Based Job Loading System

## Overview

The user query system stores personalized search queries per user in the database, enabling **quota-efficient**, **scalable**, and **personalized** job collection using Active Jobs DB's pipe operator (`|`) for OR logic.

---

## Why This Approach?

### ✅ Benefits Over Config-Based Loading

| Feature | Config-Based | **User Query-Based** |
|---------|-------------|---------------------|
| Personalization | Global for all users | ✅ Per-user customization |
| Scalability | Update config manually | ✅ Auto-scales with users |
| Quota Efficiency | Fetches all city jobs | ✅ Only user-relevant jobs |
| Flexibility | Static configuration | ✅ Dynamic per user |
| API Efficiency | Multiple API calls | ✅ Uses pipe `\|` operator |

---

## How It Works

### 1. User Uploads CV
```
User uploads CV → CV parsed by Claude → Profile extracted
```

### 2. Auto-Generate Search Queries
```python
# From CV, system generates:
- title_keywords: "data scientist|ML engineer|AI engineer"  # OR logic
- locations: "Berlin|Hamburg|Munich"                        # OR logic
- ai_work_arrangement: "Remote OK|Hybrid"                   # User preference
- ai_seniority: "Senior|Lead"                               # Based on experience
```

### 3. Daily Job Loading
```
Loader reads all user queries → Executes via Active Jobs DB → Deduplicates → Stores
```

---

## Database Schema

### `user_search_queries` Table

```sql
CREATE TABLE user_search_queries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    query_name TEXT NOT NULL,           -- e.g., "Primary Search"

    -- Search parameters (pipe-separated for OR)
    title_keywords TEXT,                -- "data scientist|ML engineer"
    locations TEXT,                     -- "Berlin|Hamburg|Munich"

    -- AI filters
    ai_work_arrangement TEXT,           -- "Remote OK|Hybrid"
    ai_employment_type TEXT,            -- "Full-time"
    ai_seniority TEXT,                  -- "Senior|Lead"
    ai_industry TEXT,                   -- "Technology|Finance"

    -- Configuration
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    max_results INTEGER DEFAULT 100,

    -- Tracking
    created_date TIMESTAMP DEFAULT NOW(),
    last_run_date TIMESTAMP,
    last_job_count INTEGER DEFAULT 0
);
```

---

## Active Jobs DB Pipe Operator

Active Jobs DB supports `|` (pipe) operator for OR logic in filters:

```python
# Single API call searches:
#   - Titles: "data scientist" OR "ML engineer" OR "AI engineer"
#   - Locations: Berlin OR Hamburg OR Munich
jobs = collector.search_all_recent_jobs(
    location="Berlin|Hamburg|Munich",
    ai_work_arrangement="Remote OK|Hybrid",
    date_posted="24h"
)
```

**Benefits:**
- ✅ One API call instead of 3×3 = 9 calls
- ✅ Massive quota savings
- ✅ Faster execution
- ✅ API-level filtering (not local)

---

## Usage

### Setup (One-Time)

```bash
# 1. Run migration to create table
python scripts/migrate_add_user_queries.py

# 2. Users upload CVs (queries auto-generated)
# OR manually create queries (see below)
```

### Daily Job Loading

```bash
# Load jobs for ALL users based on their queries
python scripts/user_query_loader.py

# Use weekly filter (for backfill)
python scripts/user_query_loader.py --date week
```

### Auto-Generation from CV

When a user uploads a CV, the system automatically:

1. Extracts `desired_job_titles` from CV
2. Extracts `preferred_work_locations` from CV
3. Determines `seniority` from years of experience
4. Maps `work_arrangement_preference` to API filters
5. Creates a "Primary Search" query

**Example:**

CV contains:
- Desired titles: ["Data Scientist", "ML Engineer", "AI Engineer"]
- Locations: ["Berlin", "Hamburg"]
- Work preference: "remote"
- 8 years experience

Generates query:
```python
{
    "query_name": "Primary Search",
    "title_keywords": "Data Scientist|ML Engineer|AI Engineer",
    "locations": "Berlin|Hamburg",
    "ai_work_arrangement": "Remote OK|Remote Solely",
    "ai_seniority": "Mid|Senior",
    "priority": 10
}
```

---

## Manual Query Management

### Add Query for User

```python
from src.database.factory import get_database

db = get_database()

# Add query
query_id = db.add_user_search_query(
    user_id=1,
    query_name="Backup Jobs",
    title_keywords="software engineer|developer",
    locations="Munich|Frankfurt",
    ai_work_arrangement="Hybrid",
    ai_seniority="Mid",
    priority=5,
    max_results=50
)
```

### Update Query

```python
# Change locations
db.update_user_search_query(
    query_id=1,
    locations="Berlin|Hamburg|Cologne"
)

# Disable query temporarily
db.update_user_search_query(
    query_id=2,
    is_active=False
)
```

### Get User's Queries

```python
queries = db.get_user_search_queries(user_id=1, active_only=True)

for query in queries:
    print(f"{query['query_name']}: {query['title_keywords']}")
```

### Delete Query

```python
db.delete_user_search_query(query_id=3)
```

---

## Example Queries

### Example 1: Multi-Role Search
```sql
INSERT INTO user_search_queries (user_id, query_name, title_keywords, locations, ai_work_arrangement)
VALUES (1, 'Primary Search',
        'data scientist|ML engineer|AI researcher',
        'Berlin|Hamburg',
        'Remote OK|Hybrid');
```

**Searches for:**
- Any of 3 titles
- In Berlin OR Hamburg
- Remote OK OR Hybrid arrangements

### Example 2: Industry-Specific
```sql
INSERT INTO user_search_queries (user_id, query_name, title_keywords, ai_industry, ai_seniority)
VALUES (1, 'Automotive Jobs',
        'data scientist|ML engineer',
        NULL,
        'Automotive',
        'Senior|Lead');
```

**Searches for:**
- Data scientist OR ML engineer
- In automotive industry
- Senior OR Lead level

### Example 3: Location-Agnostic Remote
```sql
INSERT INTO user_search_queries (user_id, query_name, title_keywords, ai_work_arrangement)
VALUES (1, 'Remote Only',
        'senior data scientist|lead ML engineer',
        NULL,
        'Remote Solely');
```

**Searches for:**
- Senior data scientist OR Lead ML engineer
- Anywhere in Germany
- Remote only positions

---

## Quota Management

### Daily Loading (24h)

With 3 users, each with 1 query:
- User 1: "data scientist|ML engineer" in "Berlin|Hamburg" → ~100 jobs
- User 2: "software engineer" in "Munich" → ~80 jobs
- User 3: "product manager" remote → ~60 jobs

**Total:** ~240 jobs/day = 7,200 jobs/month (36% of 20,000 quota) ✅

### Adding New Users

When User 4 joins and uploads CV:
- Query auto-generated
- Next daily run includes their query
- No code changes needed!

### Quota Warning

If projected monthly usage > 20,000:
1. Reduce `max_results` for some queries
2. Disable low-value queries
3. Use more specific filters
4. Contact Active Jobs DB for quota upgrade

---

## Comparison: Old vs New

### Old Approach (Config-Based)

```yaml
key_cities:
  - "Berlin"    # Fetch ALL jobs
  - "Hamburg"   # Fetch ALL jobs
```

**Problems:**
- ❌ Fetches jobs irrelevant to users
- ❌ Static - must manually update config
- ❌ Wastes quota on unwanted jobs
- ❌ Not personalized

### New Approach (User Queries)

```sql
-- User 1: Data scientist in Berlin
title_keywords: "data scientist|ML engineer"
locations: "Berlin"

-- User 2: Software engineer in Hamburg
title_keywords: "software engineer|developer"
locations: "Hamburg"
```

**Benefits:**
- ✅ Only fetches relevant jobs
- ✅ Dynamic - auto-updates with users
- ✅ Maximizes quota efficiency
- ✅ Fully personalized

---

## Best Practices

### 1. Query Naming
```python
# Good - descriptive names
"Primary Search"
"Backup Opportunities"
"Remote Leadership Roles"

# Bad - generic names
"Query 1"
"Search"
"Jobs"
```

### 2. Priority Levels
```python
priority=10  # High priority - run first
priority=5   # Medium priority
priority=0   # Low priority - run last
```

### 3. Keyword Optimization
```python
# Good - specific, pipe-separated
"data scientist|ML engineer|AI researcher"

# Bad - too broad or comma-separated
"data, scientist, ML"
```

### 4. Location Strategy
```python
# Specific cities for local jobs
locations="Berlin|Hamburg"

# NULL for remote-only
locations=None
ai_work_arrangement="Remote Solely"

# Combine both
locations="Munich|Frankfurt"  # Local opportunities
# + separate query with Remote filter
```

### 5. Max Results
```python
# Active job seeker
max_results=100

# Passive candidate
max_results=25
```

---

## Migration Path

If you're currently using config-based loading:

1. **Week 1:** Run migration, keep config-based loading
2. **Week 2:** Have existing users upload CVs (generates queries)
3. **Week 3:** Run both loaders in parallel
4. **Week 4:** Switch to user-query loader only

---

## Troubleshooting

### No Queries Found
```
⚠️ No active search queries found!
```

**Solution:** Users need to:
1. Upload CVs (triggers auto-generation), OR
2. Manually create queries in `user_search_queries` table

### Too Many Jobs
```
⚠️ WARNING: Projected 150% OVER quota!
```

**Solution:**
1. Reduce `max_results` for all queries
2. Disable low-priority queries
3. Use more specific filters

### Duplicate Jobs
```
Duplicates skipped: 145
```

This is **NORMAL** and **GOOD**:
- Multiple users may have overlapping queries
- System automatically deduplicates
- Saves database space

---

## Future Enhancements

### Web UI for Query Management
- Let users create/edit their own queries
- Visual query builder
- Preview results before saving

### Smart Query Suggestions
- Claude analyzes job application history
- Suggests new query variations
- Auto-disables low-performing queries

### Query Analytics
- Track which queries find most jobs
- Show job-to-application conversion rate
- Optimize queries automatically

---

## Summary

The user query system provides:

✅ **Personalized** job searches per user
✅ **Quota-efficient** using pipe operators
✅ **Scalable** - auto-adapts to user base
✅ **Flexible** - easy to modify queries
✅ **Automated** - works from CV upload

This is the **recommended** approach for production deployments!
