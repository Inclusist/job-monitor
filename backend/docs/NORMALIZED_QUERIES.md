# Normalized Query System - Database-Level Deduplication

## The Problem (Old Approach)

Using pipe-separated values:
```sql
user_id | title_keywords           | locations
1       | "data scientist|ML eng"  | "Berlin|Hamburg"
2       | "data scientist"         | "Berlin"
3       | "data scientist"         | "Berlin|Hamburg"
```

**Issue:** "data scientist" in "Berlin" appears in all 3 queries!
- User 1's query includes it
- User 2's query is exact match
- User 3's query includes it

**Result:** API called 3 times for same combination → **wasted 66% of quota!**

---

## The Solution (Normalized Approach)

Store each title+location combination as a separate row:

### User 1 wants: "data scientist" + "ML engineer" in "Berlin" + "Hamburg"
```sql
user_id | query_name | title_keyword      | location
1       | Primary    | "data scientist"   | "Berlin"
1       | Primary    | "data scientist"   | "Hamburg"
1       | Primary    | "ML engineer"      | "Berlin"
1       | Primary    | "ML engineer"      | "Hamburg"
```
**4 rows created**

### User 2 wants: "data scientist" in "Berlin"
```sql
user_id | query_name | title_keyword      | location
2       | Primary    | "data scientist"   | "Berlin"  ← DUPLICATE!
```
**1 row created**

### User 3 wants: "data scientist" in "Berlin" + "Hamburg"
```sql
user_id | query_name | title_keyword      | location
3       | Primary    | "data scientist"   | "Berlin"  ← DUPLICATE!
3       | Primary    | "data scientist"   | "Hamburg" ← DUPLICATE!
```
**2 rows created**

---

## Database-Level Deduplication

Simple SQL query eliminates duplicates:

```sql
SELECT DISTINCT
    title_keyword,
    location,
    ai_work_arrangement,
    ai_seniority
FROM user_search_queries
WHERE is_active = TRUE;
```

**Result:**
```sql
title_keyword      | location  | ai_work_arrangement | ai_seniority
"data scientist"   | "Berlin"  | "Remote OK"         | "Senior"
"data scientist"   | "Hamburg" | "Remote OK"         | "Senior"
"ML engineer"      | "Berlin"  | "Remote OK"         | "Senior"
"ML engineer"      | "Hamburg" | "Remote OK"         | "Senior"
```

**Only 4 unique combinations instead of 7 rows!**
**Quota saved: 3 API calls (42.9%)**

---

## Real-World Example

### Scenario: 3 Users Upload CVs

**User A (Senior Data Scientist in Berlin):**
- Titles: ["Data Scientist", "ML Engineer"]
- Locations: ["Berlin"]
- Creates: 2 rows

**User B (Data Scientist looking in Berlin and Hamburg):**
- Titles: ["Data Scientist"]
- Locations: ["Berlin", "Hamburg"]
- Creates: 2 rows

**User C (ML Engineer in Berlin):**
- Titles: ["ML Engineer", "AI Engineer"]
- Locations: ["Berlin"]
- Creates: 2 rows

**Total rows: 6**

### Deduplication

```sql
SELECT DISTINCT title_keyword, location, ...
```

Returns:
1. "Data Scientist" + "Berlin" (appears in User A, User B)
2. "Data Scientist" + "Hamburg" (User B)
3. "ML Engineer" + "Berlin" (User A, User C)
4. "AI Engineer" + "Berlin" (User C)

**Unique combinations: 4**
**Quota saved: 2 API calls (33.3%)**

---

## How Job Loading Works

### 1. Get Unique Combinations
```python
unique_combinations = db.get_unique_query_combinations()
# Returns: 4 combinations (not 6)
```

### 2. Execute Each Once
```python
for combination in unique_combinations:
    jobs = api.search(
        title=combination['title_keyword'],
        location=combination['location'],
        ...
    )
    store_jobs(jobs)  # User-agnostic storage
```

### 3. Users See Relevant Jobs
When User A views jobs:
```sql
SELECT j.*
FROM jobs j
JOIN user_search_queries usq ON (
    j.title ILIKE '%' || usq.title_keyword || '%'
    AND j.location ILIKE '%' || usq.location || '%'
)
WHERE usq.user_id = <User A ID>
```

Jobs are stored once, matched to users at retrieval time!

---

## Benefits

### ✅ Database Handles Deduplication
No complex application logic - just `SELECT DISTINCT`

### ✅ Automatic Quota Savings
The more users with similar interests, the more savings!

### ✅ Better Indexing
Separate columns → better database performance

### ✅ Simpler Code
No string parsing, no pipe operators in app code

### ✅ Flexible Queries
Easy to add/remove individual combinations

---

## Migration

Old table (pipe-separated):
```sql
CREATE TABLE user_search_queries (
    title_keywords TEXT,  -- "data scientist|ML engineer"
    locations TEXT        -- "Berlin|Hamburg"
);
```

New table (normalized):
```sql
CREATE TABLE user_search_queries (
    title_keyword TEXT,   -- "data scientist"
    location TEXT,        -- "Berlin"
    UNIQUE(user_id, query_name, title_keyword, location, ...)
);
```

Run migration:
```bash
python scripts/migrate_normalize_user_queries.py
```

---

## Example: Auto-Generation from CV

CV contains:
- Desired titles: ["Data Scientist", "ML Engineer", "AI Researcher"]
- Locations: ["Berlin", "Hamburg"]
- Work preference: "remote"
- 8 years experience

Creates **6 rows**:
```python
db.add_user_search_queries(
    user_id=1,
    query_name="Primary Search",
    title_keywords=["Data Scientist", "ML Engineer", "AI Researcher"],  # List!
    locations=["Berlin", "Hamburg"],                                     # List!
    ai_work_arrangement="Remote OK",
    ai_seniority="Senior"
)
```

Generates:
1. Data Scientist + Berlin
2. Data Scientist + Hamburg
3. ML Engineer + Berlin
4. ML Engineer + Hamburg
5. AI Researcher + Berlin
6. AI Researcher + Hamburg

If another user wants "Data Scientist" in "Berlin" → **DUPLICATE DETECTED** → Only 1 new API call needed!

---

## Quota Savings Calculator

**Formula:**
```
Total rows - Unique combinations = API calls saved
Savings % = (Saved / Total rows) × 100
```

**Example:**
- 10 users
- Average 3 titles × 2 locations = 6 rows/user
- Total rows: 60

With overlap:
- Unique combinations: 35
- Saved: 60 - 35 = **25 API calls (41.7% savings)**

---

## Summary

Your normalized approach is **brilliant** because:

1. **Leverages database strengths** - DISTINCT is what databases do best
2. **Scales automatically** - More users = More savings
3. **Simple implementation** - No complex consolidation logic
4. **Mathematically optimal** - Impossible to do better than DISTINCT
5. **Production-ready** - Standard database design pattern

This is the **right way** to solve the deduplication problem!
