
import os
import sys
import json
from typing import Dict, List, Any
from dotenv import load_dotenv
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

load_dotenv()

# --- CONFIGURATION ---
USER_ID = 93
TEST_JOB_IDS = [] # Will be populated by user input
# ---------------------

def get_db_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def load_model():
    print("📥 Loading model 'paraphrase-multilingual-MiniLM-L12-v2'...")
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def cos_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_user_profile(conn, user_id):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Get Primary CV ID
    cur.execute("SELECT id FROM cvs WHERE user_id = %s AND is_primary = 1", (user_id,))
    cv = cur.fetchone()
    if not cv:
        print(f"❌ No primary CV found for user {user_id}")
        sys.exit(1)
    
    # Get Profile Data
    cur.execute("SELECT * FROM cv_profiles WHERE cv_id = %s", (cv['id'],))
    profile = cur.fetchone()
    cur.close()
    return profile

def get_jobs(conn, job_ids):
    if not job_ids:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Cast IDs to strings just in case, though usually int
    perms = ','.join(['%s'] * len(job_ids))
    cur.execute(f"SELECT * FROM jobs WHERE id IN ({perms})", tuple(job_ids))
    jobs = cur.fetchall()
    cur.close()
    return jobs

# --- STRATEGY 1: RAW TEXT (Current Baseline) ---
def build_text_raw_cv(p):
    # Mimics current scripts/filter_jobs.py
    parts = [
        p.get('expertise_summary', ''),
        str(p.get('technical_skills', '')),
        str(p.get('work_experience', '')),
        str(p.get('education', ''))
    ]
    return " ".join(parts)[:8000] # Cap roughly

def build_text_raw_job(j):
    # Mimics current scripts/filter_jobs.py
    parts = [
        j.get('title', ''), j.get('title', ''), # Double weight
        j.get('company', ''),
        j.get('location', ''),
        j.get('description', '')[:3000]
    ]
    return " ".join(parts)

# --- STRATEGY 2: STRUCTURED SUMMARIES (Proposed) ---
def build_text_summary_cv(p):
    # Focused keywords and role info only
    skills = p.get('technical_skills', [])
    if isinstance(skills, str): skills = [skills]
    
    return f"""
    Role: {p.get('extracted_role', 'Software Engineer')}
    Experience: {p.get('total_years_experience', 0)} years
    Skills: {', '.join(skills[:20])}
    Highlights: {p.get('expertise_summary', '')[:500]}
    """

def build_text_summary_job(j):
    # Uses Enriched Metadata if available, else falls back to snippet
    skills = j.get('ai_key_skills') or []
    if isinstance(skills, str): skills = [skills] # In case DB returns string
    
    return f"""
    Job: {j.get('title', '')}
    Company: {j.get('company', '')}
    Location: {j.get('location', '')}
    Language: {j.get('ai_job_language', 'unknown')}
    Skills: {', '.join(skills)}
    Level: {j.get('ai_experience_level', '')}
    Type: {j.get('ai_employment_type', '')}
    """

# --- STRATEGY 3: SYNTHETIC QUERY (AI Generating Search Terms) ---
def generate_synthetic_queries(client, profile_text):
    prompt = f"""
    You are an expert recruiter. Based on this candidate profile, generate 2 optimal semantic search strings to find them the perfect job.
    1. English Search Query
    2. German Search Query
    
    Profile:
    {profile_text[:2000]}
    
    Output Format: JSON -> {{ "query_en": "...", "query_de": "..." }}
    """
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(resp.content[0].text)
    except:
        return {"query_en": "", "query_de": ""}

def main():
    if len(sys.argv) > 1:
        # Accept CSV of job IDs as arg
        job_ids = [int(x) for x in sys.argv[1].split(',')]
    else:
        job_ids = TEST_JOB_IDS

    if not job_ids:
        print("Usage: python compare_matching.py <job_id1,job_id2,...>")
        sys.exit(1)

    conn = get_db_connection()
    profile = get_user_profile(conn, USER_ID)
    jobs = get_jobs(conn, job_ids)
    conn.close()

    model = load_model()
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    print("\n" + "="*60)
    print(f"MATCHING EXPERIMENT | User ID: {USER_ID}")
    print("="*60)
    print(f"Candidate Experience: {profile.get('total_years_experience')} years")
    
    # 1. Pre-compute CV embeddings
    print("\nEncoding CV...")
    
    # Strategy 1 Vector
    cv_raw_vec = model.encode(build_text_raw_cv(profile))
    
    # Strategy 2 Vector
    cv_summary_vec = model.encode(build_text_summary_cv(profile))
    
    # Strategy 3 Vectors (Synthetic)
    print("Generating synthetic queries with Claude...")
    queries = generate_synthetic_queries(client, build_text_summary_cv(profile))
    print(f"  -> EN: {queries['query_en']}")
    print(f"  -> DE: {queries['query_de']}")
    q_en_vec = model.encode(queries['query_en'])
    q_de_vec = model.encode(queries['query_de'])
    
    print("\n" + "-"*60)
    
    for job in jobs:
        print(f"\nJOB {job['id']}: {job.get('title')} ({job.get('location')})")
        print(f"   [Lang: {job.get('ai_job_language') or '?'}]")
        
        # S1: Baseline
        j_raw = build_text_raw_job(job)
        j_raw_vec = model.encode(j_raw)
        score_s1 = cos_sim(cv_raw_vec, j_raw_vec)
        
        # S2: Summary
        j_sum = build_text_summary_job(job)
        j_sum_vec = model.encode(j_sum)
        score_s2 = cos_sim(cv_summary_vec, j_sum_vec)
        
        # S3: Synthetic (Max of EN or DE query)
        score_s3_en = cos_sim(q_en_vec, j_raw_vec) # Match query against raw job text (standard retrieval)
        score_s3_de = cos_sim(q_de_vec, j_raw_vec)
        score_s3 = max(score_s3_en, score_s3_de)
        
        print(f"   🔹 Baseline (Raw Text):      {score_s1:.4f}")
        print(f"   🔸 Focused Summary:          {score_s2:.4f}  <-- vs 'Perfect' Metadata")
        print(f"   ✨ Synthetic Query (Agent):  {score_s3:.4f}")

if __name__ == "__main__":
    main()
