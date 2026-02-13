# Gemini CLI Onboarding: Inclusist Project

Welcome to the Inclusist Project! This document provides a high-level overview of the system for interactive agents.

## 🚀 Project Overview
Inclusist is an AI-powered job matching platform designed to streamline the job search process through deep profile analysis, automated job collection, and intelligent matching.

- **Primary Goal:** Match users with the most relevant jobs using a two-stage AI pipeline.
- **Key Features:** CV Parsing, Semantic Matching, Deep Claude Analysis, Tailored Resume/Cover Letter Generation, and Application Tracking.

---

## 🏗️ Architecture

### Backend (Python/Flask)
- **Framework:** Flask 3.0.0
- **Database:** PostgreSQL (Production/Railway), SQLite (Local Development)
- **AI Stack:**
  - **Gemini 2.5 Flash:** CV Parsing, Preference Generation, Primary Resume/CL Generation.
  - **Claude 3.5 Haiku:** Deep Job Match Analysis, Fallback Resume/CL Generation.
  - **Sentence-Transformers:** Semantic similarity (`paraphrase-multilingual-MiniLM-L12-v2`).
- **Entry Points:** `backend/app.py` (API), `backend/scripts/daily_job_loader.py` (Cron).

### Frontend (React/TypeScript)
- **Framework:** React + Vite + Tailwind CSS.
- **State Management:** TanStack React Query (fetching/caching), React Context (Auth).
- **Key Components:**
  - `OnboardingPage.tsx`: Multi-step setup wizard.
  - `JobsPage.tsx`: Main job feed with real-time matching progress.
  - `ProfilePage.tsx`: Inline-editable CV profile.

---

## 🧠 Core AI Workflows

### 1. CV Parsing (Gemini)
- **Logic:** `backend/src/analysis/cv_analyzer.py`
- **Process:** Extracts ~30 fields from raw text, including "Abstract" fields like `derived_seniority` and `domain_expertise`. It also generates a `semantic_summary` for vector matching.

### 2. Job Matching Pipeline
- **Logic:** `backend/src/matching/matcher.py`
- **Stage 1 (Semantic):** Uses `Sentence-Transformers` to filter hundreds of jobs down to the top matches (>0.30 similarity).
- **Stage 2 (Deep Analysis):** Top matches are sent to Claude 3.5 Haiku for a detailed score (0-100), reasoning, key alignments, and gaps.
- **Progressive UI:** Matching runs in background chunks, updating the frontend in real-time.

### 3. Document Generation
- **Logic:** `backend/src/resume/resume_generator.py`
- **Output:** Tailored, ATS-optimized HTML resumes and cover letters based on specific job requirements and user competencies.

---

## 🛠️ Key Files & Directories
- `backend/config.yaml`: Central configuration for job sources, thresholds, and daily loading strategies.
- `backend/src/collectors/`: API integrations for Adzuna, ActiveJobs, and Arbeitsagentur.
- `backend/scripts/`: ~90 utility scripts for migrations, backfilling, and analysis.
- `PROJECT_ARCHITECTURE.md`: Comprehensive reference for the entire system.

---

## 🚦 Common Tasks for Gemini
- **Adding Job Sources:** Implement new collectors in `backend/src/collectors/` and update `config.yaml`.
- **Refining Matching:** Adjust prompts in `claude_analyzer.py` or thresholds in `matcher.py`.
- **Enhancing UI:** Modify React components in `frontend/src/pages/` or `frontend/src/components/`.
- **Database Migrations:** Use or create scripts in `backend/scripts/` to update Postgres/SQLite schemas.

---

## 📝 Maintenance
- **Daily Updates:** Managed by `backend/scripts/daily_job_loader.py`.
- **Logs:** Located in `backend/data/logs/`.
- **Tests:** Backend tests in `backend/tests/`, run via `pytest`.
