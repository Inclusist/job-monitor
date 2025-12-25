# Available Job Collectors

This document lists all available job collectors and their current usage in the system.

---

## Currently Active Collectors

### 1. **JSearch** (RapidAPI) - PRIMARY FOR USER MATCHING
**File:** `src/collectors/jsearch.py`  
**Used In:** User matching (`src/matching/matcher.py`)

**Features:**
- Aggregates jobs from LinkedIn, Indeed, Google Jobs, ZipRecruiter, BeBee
- RapidAPI service
- Requires API key: `JSEARCH_API_KEY`
- Country code support (de, fr, gb, es, nl, it, be, pt, ca, us)
- Date filtering: all, today, 3days, week, month

**Current Usage:**
- ✅ **First-time user matching** - Progressive batching with concurrent searches
- Fetches ~50 jobs per keyword batch (5 pages)
- Only triggered when user has no existing matches

**Pricing:** Pay-per-use via RapidAPI

---

### 2. **Arbeitsagentur** (German Federal Employment Agency)
**File:** `src/collectors/arbeitsagentur.py`  
**Used In:** Daily job updater (`scripts/daily_job_updater.py`), mass loader, scheduled scripts

**Features:**
- Official German government job API (JOBSUCHE)
- **FREE** - No registration required
- Public API key: `jobboerse-jobsuche`
- Comprehensive German job market coverage (150k-200k jobs)
- Advanced filters: job type, work time, radius, experience level

**Current Usage:**
- ✅ **Daily background job fetching** - Automated script runs daily
- ✅ **Mass loading scripts** - Bulk import of German jobs
- Used for scheduled updates, NOT for real-time user matching

**Pricing:** FREE (unlimited)

---

### 3. **Active Jobs** (RapidAPI)
**File:** `src/collectors/activejobs.py`  
**Used In:** Bulk fetch scripts, app.py manual search

**Features:**
- Collects jobs from ATS platforms and career sites
- RapidAPI service
- Requires API key: `ACTIVEJOBS_API_KEY`
- Germany coverage: 40k-50k jobs
- Source quality filtering built-in

**Current Usage:**
- Manual "Discover Jobs" feature in web UI
- Bulk fetch scripts (`scripts/bulk_fetch_jobs.py`)
- NOT used in automatic user matching

**Pricing:** 
- Free Basic: 5,000 jobs/month, 200 requests/month, 1000 requests/hour

---

### 4. **Indeed** (Publisher API)
**File:** `src/collectors/indeed.py`  
**Used In:** Legacy main.py, manual searches

**Features:**
- Indeed Publisher API
- Requires Publisher ID: `INDEED_PUBLISHER_ID`
- Global coverage
- Direct access to Indeed job listings

**Current Usage:**
- ⚠️ **Legacy/limited use** - Available but not actively used in matching
- Manual search capabilities
- Requires Indeed Publisher approval

**Pricing:** FREE (with Publisher account)

---

### 5. **Adzuna**
**File:** `src/collectors/adzuna.py`  
**Used In:** Not currently integrated

**Features:**
- Adzuna job search engine
- Requires App ID and App Key: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`
- Multi-country support (de, us, gb, fr)
- Source quality filtering

**Current Usage:**
- ❌ **Not integrated** - Code exists but not used anywhere
- Could be added as alternative collector

**Pricing:**
- Free tier: 250 calls/month

---

### 6. **Apify Stepstone**
**File:** `src/collectors/apify_stepstone.py`  
**Used In:** Unknown/legacy

**Features:**
- Stepstone job scraping via Apify
- German job market focused

**Current Usage:**
- ❌ Status unknown - May be legacy code

---

## Collector Flow Summary

### **User Matching Flow** (Real-time)
```
User clicks "Match Jobs"
    ↓
First-time user? (no existing matches)
    ↓ YES
JSearch API Progressive Fetching
    - 15 keywords → 8 batches (2 keywords each)
    - All batches run concurrently
    - ~72 jobs fetched in 33s
    - Jobs added to database
    ↓
Semantic Matching
    - Match against ALL jobs in database (~2,090 jobs)
    - Includes: JSearch jobs + Arbeitsagentur jobs + any other sources
    ↓
Claude Analysis (top 8 jobs ≥70%)
```

### **Daily Background Update** (Scheduled)
```
Cron job runs daily (6 AM)
    ↓
scripts/daily_job_updater.py
    ↓
Arbeitsagentur Collector
    - Fetches jobs from last 24h
    - Based on ALL users' keywords
    - Deduplicates searches
    - Free and unlimited
    ↓
Database updated with fresh German jobs
```

---

## Recommendations

### **Current Setup (Working Well):**
1. **JSearch for user matching** - Broad international coverage, fast API
2. **Arbeitsagentur for daily updates** - Free, comprehensive German jobs
3. Users get: JSearch (international) + Arbeitsagentur (German) = Best of both

### **Potential Improvements:**

#### Option 1: Add Arbeitsagentur to User Matching
**Pros:**
- More German jobs in real-time
- FREE (no API costs)
- Official government source

**Cons:**
- Additional API calls (30-60s more)
- Already covered by daily updater
- May return duplicates

#### Option 2: Use Active Jobs Instead of JSearch
**Pros:**
- Lower cost (free tier available)
- ATS platform coverage

**Cons:**
- Limited free tier (200 requests/month)
- Smaller coverage than JSearch
- JSearch aggregates LinkedIn which Active Jobs doesn't

#### Option 3: Add Adzuna as Fallback
**Pros:**
- Free tier available
- Good coverage
- Can use when JSearch quota exceeded

**Cons:**
- Limited to 250 calls/month (free tier)
- Would need integration work

---

## Current Production Setup (Recommended)

**Keep as-is:**
- ✅ **JSearch** for first-time user matching (progressive batching)
- ✅ **Arbeitsagentur** for daily background updates (free)
- ✅ Database accumulates jobs from both sources
- ✅ All users benefit from daily updates without API costs

**Future consideration:**
- Add manual "Refresh Jobs" button that triggers JSearch on-demand
- Integrate Adzuna as overflow when JSearch quota is reached
- Add Arbeitsagentur to user matching if German-specific jobs needed faster

---

**Last Updated:** 2025-12-25
