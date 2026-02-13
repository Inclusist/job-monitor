# Inclusist Job Monitor - Project Architecture

> A comprehensive reference document for understanding the entire codebase. One read should give any developer or AI tool full context to work on any part of the system.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack](#2-tech-stack)
3. [Directory Structure](#3-directory-structure)
4. [Database Schema](#4-database-schema)
5. [Backend Architecture](#5-backend-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Data Flow by User Journey](#7-data-flow-by-user-journey)
8. [AI/ML Pipeline](#8-aiml-pipeline)
9. [Job Collection Pipeline](#9-job-collection-pipeline)
10. [Environment & Configuration](#10-environment--configuration)
11. [Design System](#11-design-system)
12. [Key Patterns & Conventions](#12-key-patterns--conventions)

---

## 1. System Overview

Inclusist is an AI-powered job matching platform. Users upload their CV, and the system:
1. Parses the CV using Gemini AI to extract structured profile data
2. Fetches jobs from multiple sources (Adzuna, ActiveJobs, Arbeitsagentur, etc.)
3. Matches jobs using a two-stage pipeline: semantic embedding similarity + Claude AI deep analysis
4. Generates tailored resumes and cover letters for specific job applications
5. Tracks applications through a pipeline dashboard

The system is a monolithic Flask backend serving both legacy HTML templates and a modern React SPA frontend.

---

## 2. Tech Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Flask | 3.0.0 |
| Database | PostgreSQL (prod) / SQLite (dev) | - |
| Auth | Flask-Login + Authlib (OAuth 2.0) | 0.6.3 / 1.3.0 |
| AI (CV Parsing) | Google Gemini | gemini-2.5-flash |
| AI (Job Analysis) | Anthropic Claude | claude-3-5-haiku |
| AI (Resume/CL Gen) | Gemini (primary) + Claude (fallback) | - |
| Semantic Matching | sentence-transformers | >=2.2.0 |
| PDF Parsing | pdfplumber | 0.10.3 |
| PDF Generation | WeasyPrint | 67.0 |
| WSGI Server | Gunicorn | 21.2.0 |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React + TypeScript | 18.3.1 / 5.5.3 |
| Build Tool | Vite | 5.4.2 |
| Styling | Tailwind CSS | 3.4.1 |
| State/Data | TanStack React Query | 5.90.20 |
| HTTP Client | Axios | 1.13.5 |
| Animations | Framer Motion | 12.33.0 |
| Icons | Lucide React | 0.344.0 |
| Routing | React Router DOM | 7.13.0 |

---

## 3. Directory Structure

```
inclusist-project/
├── backend/
│   ├── app.py                          # Main Flask app (~5000 lines, all routes)
│   ├── config.yaml                     # Job source config, daily loading, thresholds
│   ├── requirements.txt                # Python dependencies
│   ├── src/
│   │   ├── analysis/
│   │   │   ├── cv_analyzer.py          # Gemini CV parser (primary)
│   │   │   ├── cv_analyzer_v2.py       # Enhanced parser with semantic fields
│   │   │   ├── claude_analyzer.py      # Claude job-user match scoring
│   │   │   ├── semantic_matcher.py     # Sentence-transformer similarity
│   │   │   ├── cover_letter_generator.py
│   │   │   ├── feedback_learner.py     # Learns from user feedback
│   │   │   ├── search_suggester.py     # AI search parameter suggestions
│   │   │   ├── skill_normalizer.py     # Skill deduplication & normalization
│   │   │   └── project_formatter.py    # Format projects for resumes
│   │   ├── cv/
│   │   │   └── cv_handler.py           # CV upload orchestration pipeline
│   │   ├── collectors/
│   │   │   ├── adzuna.py               # Adzuna job API
│   │   │   ├── activejobs.py           # ActiveJobs DB (36 ATS platforms)
│   │   │   ├── arbeitsagentur.py       # German Federal Employment Agency
│   │   │   ├── jsearch.py              # Indeed/LinkedIn aggregation
│   │   │   └── source_filter.py        # Quality filtering
│   │   ├── database/
│   │   │   ├── factory.py              # Auto-select SQLite or PostgreSQL
│   │   │   ├── operations.py           # SQLite job operations
│   │   │   ├── postgres_operations.py  # PostgreSQL job operations
│   │   │   ├── cv_operations.py        # SQLite user/CV operations
│   │   │   ├── postgres_cv_operations.py   # PostgreSQL user/CV operations
│   │   │   └── postgres_resume_operations.py # Resume/CL storage
│   │   ├── matching/
│   │   │   └── matcher.py              # Background matching pipeline
│   │   ├── parsers/
│   │   │   └── cv_parser.py            # PDF/DOCX/TXT text extraction
│   │   ├── resume/
│   │   │   └── resume_generator.py     # Tailored resume generation
│   │   └── utils/
│   │       ├── helpers.py              # Logging, config, deduplication
│   │       ├── job_loader.py           # Background job fetching
│   │       └── json_repair.py          # Fix malformed AI JSON
│   └── scripts/                        # ~92 utility scripts (cron, migration, analysis)
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx         # Marketing splash (unauthenticated)
│   │   │   ├── LoginPage.tsx           # OAuth login (Google/LinkedIn)
│   │   │   ├── OnboardingPage.tsx      # 6-step setup wizard
│   │   │   ├── JobsPage.tsx            # Main job browsing (~710 lines)
│   │   │   ├── DashboardPage.tsx       # Application pipeline tracker
│   │   │   ├── DocumentsPage.tsx       # Resume/CL library
│   │   │   ├── ProfilePage.tsx         # Profile management (~1220 lines)
│   │   │   └── PreferencesPage.tsx     # Search preferences editor
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx          # Nav bar with auth-aware menu
│   │   │   │   ├── Footer.tsx          # Page footer
│   │   │   │   └── ProtectedRoute.tsx  # Auth + onboarding guard
│   │   │   ├── ui/
│   │   │   │   ├── Badge.tsx           # Priority/status badges
│   │   │   │   ├── ScoreDisplay.tsx    # Color-coded match scores
│   │   │   │   ├── FilterBar.tsx       # Job filter sidebar
│   │   │   │   ├── MatchingProgress.tsx # Real-time matching progress
│   │   │   │   └── SlideOver.tsx       # Side panel for details
│   │   │   ├── onboarding/
│   │   │   │   ├── SetPreferencesStep.tsx  # AI-assisted preference setup
│   │   │   │   └── MatchingProgressStep.tsx # Onboarding matching display
│   │   │   └── JobDetailPanel.tsx      # Full job detail view
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx          # Global auth state via /api/me
│   │   ├── hooks/
│   │   │   ├── useJobs.ts              # Job list query + mutations
│   │   │   ├── useMatchingStatus.ts    # Polling with progressive refresh
│   │   │   └── useJobDetail.ts         # Single job detail query
│   │   ├── services/
│   │   │   ├── api.ts                  # Axios instance with 401 redirect
│   │   │   ├── auth.ts                 # Auth endpoints
│   │   │   ├── jobs.ts                 # Job/resume/CL/dashboard APIs
│   │   │   ├── profile.ts             # Profile CRUD APIs
│   │   │   ├── onboarding.ts          # Onboarding step APIs
│   │   │   ├── matching.ts            # Matching trigger/status APIs
│   │   │   ├── generatePreferences.ts # AI preference generation
│   │   │   └── searchQueries.ts       # Search query prefill
│   │   └── types/
│   │       └── index.ts               # All TypeScript interfaces
│   ├── vite.config.ts                  # Dev proxy to Flask :8080
│   └── tailwind.config.js
```

---

## 4. Database Schema

### Core Tables

**users** - User accounts
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| email | TEXT UNIQUE | |
| password_hash | TEXT | NULL for OAuth users |
| name | TEXT | |
| provider | TEXT | 'google', 'linkedin', 'email' |
| avatar_url | TEXT | |
| preferences | TEXT (JSON) | Search keywords, locations, OAuth metadata |
| last_filter_run | TIMESTAMP | When matching last ran |
| onboarding_completed | BOOLEAN | |
| onboarding_step | INTEGER | Current step (0-5) |

**cvs** - CV file metadata
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| user_id | FK → users | |
| file_name, file_path, file_type | TEXT | Physical file in `data/cvs/` |
| file_hash | TEXT | SHA256 for duplicate detection |
| is_primary | INTEGER | Flag for active CV |
| status | TEXT | 'active' or 'deleted' |

**cv_profiles** - Parsed CV data (one per CV)
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| cv_id | FK → cvs | |
| user_id | FK → users | |
| technical_skills | TEXT (JSON) | ["Python", "ML", ...] |
| soft_skills | TEXT (JSON) | |
| competencies | TEXT (JSON) | [{name, evidence}, ...] |
| work_history | TEXT (JSON) | [{title, company, duration, description, key_achievements}, ...] |
| expertise_summary | TEXT | Executive bio |
| semantic_summary | TEXT | AI-generated profile overview |
| extracted_role | TEXT | Canonical job title |
| derived_seniority | TEXT | Junior/Mid/Senior/Staff/Principal/Head |
| domain_expertise | TEXT (JSON) | ["Fintech", "AdTech", ...] |
| search_keywords_abstract | TEXT | Space-separated keywords for embeddings |
| user_claimed_competencies | JSONB | User-verified competencies with evidence |
| user_claimed_skills | JSONB | User-verified skills with evidence |
| raw_analysis | TEXT | Full Gemini response |

**jobs** - Global job catalog (shared across users)
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| external_id | TEXT UNIQUE | From job source |
| source | TEXT | 'adzuna', 'activejobs', etc. |
| title, company, location | TEXT | |
| description | TEXT | Full job description |
| url | TEXT | Original posting URL |
| posted_date, discovered_date | TIMESTAMP | |
| ai_competencies | JSONB | Claude-extracted required competencies |
| ai_key_skills | JSONB | Claude-extracted skills |
| ai_work_arrangement | TEXT | 'remote', 'hybrid', 'onsite' |
| ai_experience_level | TEXT | |
| ai_core_responsibilities | TEXT | |
| ai_requirements_summary | TEXT | |
| is_duplicate | BOOLEAN | |
| status | TEXT | 'new', 'applied', 'deleted' |

**user_job_matches** - Per-user match scores
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| user_id | FK → users | |
| job_id | FK → jobs | |
| semantic_score | INTEGER | 0-100, from sentence-transformer |
| claude_score | INTEGER | 0-100, from Claude analysis |
| priority | TEXT | 'high', 'medium', 'low' |
| match_reasoning | TEXT | Claude's explanation |
| key_alignments | TEXT (JSON) | Strength matches |
| potential_gaps | TEXT (JSON) | Skill gaps |
| status | TEXT | 'new', 'viewed', 'shortlisted', 'applied', 'deleted' |
| UNIQUE(user_id, job_id) | | One match per user-job pair |

**user_search_queries** - Normalized search combinations
| Column | Type | Notes |
|--------|------|-------|
| user_id | FK → users | |
| query_name | TEXT | e.g., 'Onboarding Preferences' |
| title_keyword | TEXT | Single keyword |
| location | TEXT | e.g., "Berlin, Germany" |
| ai_work_arrangement | TEXT | Pipe-separated: "remote\|hybrid" |
| priority | INTEGER | Execution order |
| is_active | BOOLEAN | |

**user_generated_resumes** - Generated resumes
| Column | Type | Notes |
|--------|------|-------|
| user_id | FK → users | |
| job_id | FK → jobs | |
| resume_html | TEXT | Generated HTML |
| resume_pdf_data | BYTEA | PDF binary |
| selections_used | JSONB | Which competencies/skills were selected |

**skill_canonical_map** - Skill normalization (global)
| Column | Type | Notes |
|--------|------|-------|
| variant | TEXT PK | Lowercase observed term |
| canonical | TEXT | Display form |
| source | TEXT | 'static', 'embedding', 'auto' |

### Entity Relationships
```
users 1──→ N cvs 1──→ N cv_profiles
users 1──→ N user_job_matches N←──1 jobs
users 1──→ N user_search_queries
users 1──→ N user_generated_resumes N←──1 jobs
users 1──→ N job_feedback N←──1 jobs
```

---

## 5. Backend Architecture

### app.py Route Groups (~5000 lines)

The monolithic Flask app is organized by functional area:

| Area | Lines (approx) | Key Routes |
|------|----------------|------------|
| **Init & Config** | 45-240 | DB factory, OAuth setup, CORS, ProxyFix |
| **Auth (OAuth)** | 240-590 | `/login/google`, `/login/linkedin`, `/authorize`, `/logout` |
| **CV Management** | 590-1074, 2914-2990 | `/api/upload-cv`, `/api/delete-cv/<id>`, `/api/set-primary-cv/<id>` |
| **Job Browsing** | 1075-1700, 3218-3457 | `/api/jobs`, `/api/jobs/<id>`, `/api/jobs/<id>/hide` |
| **Resume/CL Generation** | 1703-1950, 3951-4487 | `/api/generate-resume/<id>`, `/api/generate-cover-letter/<id>`, `/api/save-resume/<id>` |
| **Job Status & Dashboard** | 1949-2340, 4710-4825 | `/api/dashboard`, `/api/jobs/<id>/update-status`, `/api/jobs/<id>/shortlist` |
| **Documents** | 2341-2567, 4488-4709 | `/api/documents`, `/api/resumes/<id>`, `/api/cover-letters/<id>` |
| **Search Preferences** | 2616-2748, 3137-3217 | `/api/search-preferences`, `/api/update-search-preferences` |
| **Job Matching** | 2755-2832, 3458-3538 | `/api/run-matching`, `/api/matching-status`, `/api/search-jobs` |
| **Profile** | 2833-2913, 2990-3074 | `/api/profile`, `PUT /api/profile`, `DELETE /api/profile/delete` |
| **Onboarding** | 3075-3136 | `/api/onboarding/status`, `/update`, `/complete`, `/skip` |
| **Stats & Admin** | 3618-3887 | `/api/stats`, `/admin/clear-model-cache` |
| **Competency Claims** | 3888-3950 | `/api/save-competency-evidence` |
| **AI Preferences** | 4826-4992 | `/api/search-queries`, `/api/generate-preferences` |

### Key Backend Modules

**`src/analysis/cv_analyzer.py`** - Parses CVs using Gemini
- Input: Raw CV text
- Output: Structured profile JSON (skills, experience, education, competencies, etc.)
- Uses `gemini-2.5-flash` with detailed extraction prompt
- Retry logic (2 attempts), JSON repair for malformed responses

**`src/analysis/claude_analyzer.py`** - Scores job-user fit using Claude
- Input: User profile + job description
- Output: Score (0-100), reasoning, key alignments, potential gaps
- Uses `claude-3-5-haiku-20241022`
- Incorporates domain expertise as a score boosting signal
- Integrates with `FeedbackLearner` for personalized scoring

**`src/analysis/semantic_matcher.py`** - Vector similarity matching
- Model: `paraphrase-multilingual-MiniLM-L12-v2` (multilingual)
- Singleton pattern with lazy loading
- `compute_similarity(text1, text2)` → cosine similarity 0-1
- `match_competencies(job_comps, user_comps, threshold=0.45)` → mappings

**`src/matching/matcher.py`** - Background matching orchestration
- Splits jobs into date-based chunks for progressive processing
- Pipeline: semantic pre-filter → Claude deep analysis (top N only)
- Updates `matching_status` global dict (polled by frontend)
- Generates news snippets via Gemini for display during wait

**`src/cv/cv_handler.py`** - CV upload pipeline
- Validates file → extracts text (CVParser) → parses (CVAnalyzer) → stores in DB
- Calculates file hash for duplicate detection
- Auto-generates search preferences from CV data
- Auto-generates search queries (title × location combinations)

**`src/resume/resume_generator.py`** - Tailored resume generation
- Dual API: Gemini (primary, faster) → Claude (fallback)
- Analyzes job requirements + user competency mappings
- Produces ATS-optimized HTML with professional formatting
- PDF generation via WeasyPrint

**`src/analysis/skill_normalizer.py`** - Skill deduplication pipeline
1. German → English mapping (with umlaut variants)
2. DB canonical map (`skill_canonical_map` table, refreshed every 5 min)
3. Static semantic aliases
4. Case normalization

**`src/database/factory.py`** - Database abstraction
- Auto-selects PostgreSQL (via `DATABASE_URL`) or SQLite (fallback)
- Both backends implement identical interfaces (drop-in swap)
- PostgreSQL uses `ThreadedConnectionPool` (min=2, max=20)

---

## 6. Frontend Architecture

### Pages

**`LandingPage.tsx`** - Marketing page for unauthenticated users. Hero section, feature cards, CTA. No API calls.

**`LoginPage.tsx`** - OAuth login with Google and LinkedIn buttons. Redirects authenticated users to `/jobs`.

**`OnboardingPage.tsx`** - 6-step wizard: Welcome → Upload CV → Review Profile → Set Preferences → Matching Progress → Complete. Each step is an animated card component. Progress persisted to backend. Can be skipped.

**`JobsPage.tsx`** (~710 lines) - Main interface. Shows "New Matches" and "Previous Jobs" sections with filter sidebar (priority, status, min score). Includes search, matching trigger with real-time progress, job detail slide-over panel.

**`DashboardPage.tsx`** - Application pipeline tracker with status tabs (Planning, Applied, Interviewing, Offered, Rejected). Status changes via dropdown. Links to attached resumes/cover letters.

**`ProfilePage.tsx`** (~1220 lines) - Most complex page. Inline-editable sections: User Info, CV Management, Profile Summary, AI Summary, Skills, Competencies, Projects, Work Experience, Education, Languages, Claimed Items, Danger Zone (account deletion).

**`PreferencesPage.tsx`** - Search preferences with structured Country + Cities location fields (stored as "City, Country" pairs) and multi-select work arrangement (remote/hybrid/onsite).

**`DocumentsPage.tsx`** - Library of generated resumes and cover letters. View, edit, download (HTML/PDF/TXT), delete.

### Key Components

**`ProtectedRoute.tsx`** - Route guard: loading → check auth → check onboarding → render children.

**`MatchingProgress.tsx`** (Jobs page) - Real-time matching display with stage timeline pills, progress bar, counters, news snippets. Auto-dismisses after completion.

**`MatchingProgressStep.tsx`** (Onboarding) - Same visual style as jobs page version, plus step explanations describing what each matching stage does. Shows "See My Results" button on completion.

**`SetPreferencesStep.tsx`** (Onboarding) - AI-assisted preference setup. "Generate with AI" button calls Gemini to suggest categorized job titles (Similar Roles, Career Advancement, Alternative Paths) plus country/cities. Accept/decline pill UI for each suggestion.

**`JobDetailPanel.tsx`** - Slide-over with full job detail: description, AI-extracted metadata, match score, reasoning, alignments, gaps, competency/skill mappings. Actions: generate resume, generate cover letter, shortlist, analyze.

### Data Layer

**`AuthContext.tsx`** - Global auth state. Calls `GET /api/me` on init. Provides `user`, `stats`, `isAuthenticated`, `refreshAuth()`.

**`useJobs.ts`** - React Query hook for job list with filter params. Mutations for hide and run-matching with cache invalidation.

**`useMatchingStatus.ts`** - Polls matching status every 1.5s while running. Progressive cache invalidation: refreshes jobs when `chunks_completed` increases, and on final completion.

**`services/api.ts`** - Axios instance with `withCredentials: true` for cookies. 401 interceptor redirects to `/login`.

**`services/jobs.ts`** - Central API service: getJobs, hideJob, analyzeJob, runMatching, generateResume, generateCoverLetter, searchJobs, shortlistJob, getDashboard, getDocuments, etc.

### Routing & Proxy

Vite dev server proxies these paths to Flask at `http://localhost:8080`:
- `/api/*` - All API endpoints
- `/login/google`, `/login/linkedin` - OAuth initiation
- `/authorize` - OAuth callback
- `/logout` - Session termination
- `/download/*` - File downloads

---

## 7. Data Flow by User Journey

### New User Signup
```
GET /login/google → Google OAuth → POST /authorize callback
  → get_or_create_oauth_user() → INSERT INTO users
  → Redirect to FRONTEND_URL/jobs
  → ProtectedRoute detects onboarding_completed=false → /onboarding
```

### CV Upload (Onboarding Step 2)
```
POST /api/upload-cv (multipart)
  → CVParser.extract_text() → raw text from PDF/DOCX
  → CVAnalyzer.analyze_cv() → Gemini parses into structured JSON
  → INSERT INTO cvs (file metadata)
  → INSERT INTO cv_profiles (parsed profile data)
  → _auto_generate_search_preferences() → UPDATE users.preferences
  → _auto_generate_search_queries() → INSERT INTO user_search_queries
```

### Set Preferences (Onboarding Step 4)
```
POST /api/update-search-preferences
  Body: { keywords: [...], locations: ["Berlin, Germany", "Remote"], work_arrangements: ["remote", "hybrid"] }
  → UPDATE users.preferences JSON
  → Deactivate old user_search_queries
  → Create new rows: each keyword × each location = N rows
  → Store work_arrangements as pipe-separated: "remote|hybrid"
```

### Job Matching
```
POST /api/run-matching → spawns background thread
  → matcher.run_background_filtering(user_id)
    Stage 1: Load sentence-transformer model
    Stage 2: Fetch unmatched jobs for user's locations
    Stage 3: Compute semantic similarity (CV embedding vs job embedding)
    Stage 4: INSERT INTO user_job_matches (semantic_score)
    Stage 5: Top semantic matches → Claude deep analysis
    Stage 6: UPDATE user_job_matches SET claude_score, reasoning, alignments, gaps

Frontend polls GET /api/matching-status every 1.5s
  → Returns { status, stage, progress, matches_found, jobs_analyzed, news_snippets }
  → Progressive job list refresh as chunks complete
```

### Resume Generation
```
POST /api/generate-resume/<job_id>
  Body: { selections: [{name, type, evidence, work_experience_ids}], instructions, language }
  → Save claimed competencies/skills to cv_profiles
  → ResumeGenerator.generate_resume_html(profile, job, claimed_data, instructions)
    → Gemini (primary) or Claude (fallback)
  → INSERT INTO user_generated_resumes (html, pdf_data, selections_used)
```

### Job Application Tracking
```
POST /api/jobs/<id>/shortlist → UPDATE user_job_matches SET status='shortlisted'
POST /api/jobs/<id>/update-status → UPDATE status to 'applied'/'interviewing'/'offered'/'rejected'
GET /api/dashboard → Returns jobs grouped by status with attached documents
```

---

## 8. AI/ML Pipeline

### CV Parsing (Gemini)
- **Model**: `gemini-2.5-flash`
- **Input**: Raw CV text
- **Output**: ~30 structured fields (skills, experience, competencies, seniority, domain expertise, semantic summary, etc.)
- **Prompt**: Detailed extraction schema with examples for each field
- **Key instruction**: `description` = 1-2 sentence role summary; `key_achievements` = distinct bullet accomplishments (no duplication)

### Job Matching - Stage 1: Semantic (sentence-transformers)
- **Model**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Method**: Cosine similarity between CV `search_keywords_abstract` embedding and job description embedding
- **Threshold**: Jobs with similarity > threshold proceed to Stage 2
- **Speed**: Processes hundreds of jobs in seconds

### Job Matching - Stage 2: Claude Analysis
- **Model**: `claude-3-5-haiku-20241022`
- **Input**: User profile summary + job description + domain expertise
- **Output**: Score (0-100), match reasoning, key alignments, potential gaps, priority
- **Scoring signals**: Skills overlap, seniority match, domain match (boost), competency mappings
- **Personalization**: FeedbackLearner adjusts based on user's past accept/reject patterns

### Preference Generation (Gemini)
- **Model**: `gemini-2.5-flash`
- **Input**: CV profile summary (role, experience, skills, location)
- **Output**: Categorized job titles (current_level, advancement, career_pivot), country, cities, work arrangement
- **Key constraint**: Locations strictly anchored to CV data, never invented

### Resume/Cover Letter Generation
- **Primary**: Gemini `gemini-2.5-flash` (faster)
- **Fallback**: Claude `claude-3-5-haiku-20241022` (more reliable)
- **Input**: User profile + job requirements + claimed competencies + user instructions
- **Output**: ATS-optimized HTML → PDF via WeasyPrint
- **Cover letter styles**: Professional, Technical, Results-driven, Conversational, Enthusiastic, Executive

---

## 9. Job Collection Pipeline

### Sources

| Source | API | Coverage | Rate Limits |
|--------|-----|----------|-------------|
| Adzuna | REST API | Multi-country (de, us, gb, fr) | 250 calls/month |
| ActiveJobs | RapidAPI | 36 ATS platforms, 40-50k DE jobs | 5,000 jobs/month |
| Arbeitsagentur | Public API | German Federal Employment Agency | Unlimited |
| JSearch | RapidAPI | Indeed + LinkedIn aggregation | Varies by plan |

### Pipeline
```
Collector.search_jobs(keywords, location, filters)
  → Normalize to standard schema
  → SourceFilter quality check
  → job_db.add_job() → INSERT INTO jobs ON CONFLICT (external_id) DO UPDATE
  → Jobs stored globally (not user-specific)
  → User matching happens separately via user_job_matches
```

### Daily Loading
- Configured in `config.yaml` under `daily_loading`
- Key cities, flexible work arrangements, max pages per source
- Cron via `scripts/daily_job_loader.py` or `daily_job_cron.py`

---

## 10. Environment & Configuration

### Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (Railway format) |
| `ANTHROPIC_API_KEY` | Claude API for matching, resume, cover letter |
| `GOOGLE_GEMINI_API_KEY` | Gemini API for CV parsing, preference generation |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth |
| `FRONTEND_URL` | React app URL (default: `http://localhost:5173`) |
| `SECRET_KEY` | Flask session secret |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ENABLE_GEMINI` | Use Gemini for resume/CL generation | `false` |
| `MIN_MATCH_SCORE` | Minimum display threshold | 60 |
| `HIGH_PRIORITY_THRESHOLD` | Score for "high" priority | 85 |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Adzuna job source | - |
| `ACTIVEJOBS_API_KEY` | ActiveJobs source | - |
| `JSEARCH_API_KEY` | JSearch source | - |

### config.yaml Structure
- `job_sources`: Enable/disable each collector
- `search_config`: Default keywords, locations, industries
- `daily_loading`: Cities, work arrangements, max pages
- `preferences`: Score thresholds, digest settings

### Development Setup
```bash
# Backend
cd backend && pip install -r requirements.txt
python app.py  # Runs on :8080

# Frontend
cd frontend && npm install
npm run dev    # Runs on :5173, proxies /api to :8080
```

### Production (Railway)
- PostgreSQL via `DATABASE_URL`
- ProxyFix middleware for HTTPS behind reverse proxy
- Cross-origin cookies for session handling
- Gunicorn WSGI server

---

## 11. Design System

### Colors
| Role | Class | Hex |
|------|-------|-----|
| Primary | `cyan-600` | #0891b2 |
| Primary hover | `cyan-500` | #06b6d4 |
| Background | `white` / `cyan-50` | |
| Text heading | `slate-900` | |
| Text body | `slate-600` | |
| Borders | `cyan-200` | |
| Success | `emerald-500` | |
| Warning | `amber-500` | |
| Error | `rose-500` | |

### Component Patterns
```
Cards:    border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm
Buttons:  px-X py-Y bg-cyan-600 text-white rounded-xl font-semibold hover:bg-cyan-500
Inputs:   border border-cyan-200 rounded-lg px-4 py-3 focus:ring-2 focus:ring-cyan-400
Badges:   Colored by priority (emerald/amber/rose) or status
```

### Score Color Thresholds
| Score | Color | Class |
|-------|-------|-------|
| 85+ | Green | `emerald` |
| 70+ | Cyan | `cyan` |
| 50+ | Amber | `amber` |
| <50 | Gray | `slate` |

---

## 12. Key Patterns & Conventions

### Backend Patterns
- **Dual route stack**: HTML routes (Flask templates) + JSON routes (`/api/*`) for React SPA
- **Auth**: JSON 401 for `/api/*` routes, HTML redirect for non-API routes
- **Background processing**: `threading.Thread(daemon=True)` for matching and job loading
- **Global state**: `matching_status` dict keyed by `user_id` for progress tracking
- **Database abstraction**: Factory pattern auto-selects SQLite/PostgreSQL with identical interfaces
- **AI fallback**: Gemini primary → Claude fallback for generation tasks
- **`get_user_context()`**: Returns `(user_dict, stats_dict)`, used by most routes
- **Search queries normalization**: Each keyword × location = separate DB row for deduplication

### Frontend Patterns
- **React Query**: All data fetching via `useQuery`/`useMutation` with intelligent cache invalidation
- **Progressive refresh**: Jobs list refreshes as matching chunks complete (not just at end)
- **Optimistic updates**: Competency claiming updates UI immediately, reverts on API failure
- **Inline editing**: ProfilePage sections toggle between display and edit mode
- **Location format**: Stored as "City, Country" pairs internally; displayed as separate Country + Cities fields
- **Work arrangement**: Stored as pipe-separated string in DB ("remote|hybrid|onsite"); array in frontend

### Key Scripts
| Script | Purpose |
|--------|---------|
| `daily_job_loader.py` | Automated daily job fetching |
| `daily_job_cron.py` | Cron scheduler |
| `bulk_fetch_jobs.py` | One-time bulk import |
| `enrich_missing_jobs.py` | Add missing AI fields to existing jobs |
| `encode_existing_jobs.py` | Generate semantic embeddings |
| `backfill_claude_scores.py` | Score existing jobs with Claude |
| `optimize_database.py` | DB optimization and indexing |
