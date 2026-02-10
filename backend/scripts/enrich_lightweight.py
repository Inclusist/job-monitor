"""
Lightweight Job Enrichment Script
Extracts only essential fields for pre-filtering: location, work arrangement, employment type
Costs ~$0.0003 per job vs $0.00088 for full enrichment (66% cheaper)
"""
import os
import sys
import time
from dotenv import load_dotenv
from anthropic import Anthropic
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def create_lightweight_prompt(job):
    """Create minimal prompt to extract only location/work/employment fields"""
    return f"""Extract ONLY these fields from this job posting. Be concise.

JOB:
Title: {job.get('title', 'Unknown')}
Company: {job.get('company', 'Unknown')}
Location: {job.get('location', '')}
Description: {job.get('description', '')[:2000]}

OUTPUT (JSON only):
{{
  "work_arrangement": "On-site" | "Hybrid" | "Remote",
  "employment_type": ["FULL_TIME" | "PART_TIME" | "CONTRACT" | "INTERN"],
  "experience_level": "Student" | "Entry Level" | "Mid Level" | "Senior" | "Lead" | "Executive",
  "cities": ["CityName"],
  "country_code": "de" | "us" | "gb" | etc
}}

RULES:
- work_arrangement: Infer from description if not explicit
- cities: Extract mentioned cities (max 2)
- country_code: ISO 2-letter code from location
- Output PURE JSON only, no markdown
"""

def parse_llm_response(response_text):
    """Parse JSON from LLM response"""
    try:
        clean = response_text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return json.loads(clean.strip())
    except:
        return None

def enrich_job_lightweight(client, job):
    """Extract only lightweight fields from a job"""
    try:
        prompt = create_lightweight_prompt(job)
        
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,  # Much smaller! Only need ~100 tokens
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return parse_llm_response(response.content[0].text)
    except Exception as e:
        logger.error(f"Error enriching job {job.get('id')}: {e}")
        return None

def update_job_lightweight(conn, job_id, data):
    """Update job with lightweight fields only"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE jobs 
            SET 
                ai_work_arrangement = %s,
                ai_employment_type = %s,
                ai_experience_level = %s,
                cities_derived = %s,
                source_type = 'lightweight_enriched',
                last_updated = NOW()
            WHERE id = %s
        """, (
            data.get('work_arrangement'),
            data.get('employment_type', []),
            data.get('experience_level'),
            data.get('cities', []),
            job_id
        ))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"DB error updating job {job_id}: {e}")
        return False

def run_lightweight_enrichment(limit=100):
    """Run lightweight enrichment on unenriched jobs"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    db_url = os.getenv('DATABASE_URL')
    
    if not api_key or not db_url:
        logger.error("Missing ANTHROPIC_API_KEY or DATABASE_URL")
        return
    
    client = Anthropic(api_key=api_key)
    conn = psycopg2.connect(db_url)
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find jobs without lightweight enrichment
        cursor.execute("""
            SELECT id, title, company, location, description 
            FROM jobs 
            WHERE (source_type IS NULL OR source_type = '')
            AND description IS NOT NULL
            LIMIT %s
        """, (limit,))
        
        jobs = cursor.fetchall()
        cursor.close()
        
        logger.info(f"Found {len(jobs)} jobs to enrich (lightweight)")
        
        success_count = 0
        failed_count = 0
        
        for idx, job in enumerate(jobs, 1):
            logger.info(f"[{idx}/{len(jobs)}] {job['title']}")
            
            data = enrich_job_lightweight(client, dict(job))
            
            if data:
                if update_job_lightweight(conn, job['id'], data):
                    success_count += 1
                    logger.info(f"  ✓ Work: {data.get('work_arrangement')}, Type: {data.get('employment_type')}")
                else:
                    failed_count += 1
            else:
                failed_count += 1
            
            # Small delay to avoid rate limits
            if idx < len(jobs):
                time.sleep(0.3)
        
        logger.info(f"\nCompleted: {success_count} success, {failed_count} failed")
        logger.info(f"Estimated cost: ${success_count * 0.0003:.2f}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=100, help='Number of jobs to process')
    args = parser.parse_args()
    
    run_lightweight_enrichment(limit=args.limit)
