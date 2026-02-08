
import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from anthropic import Anthropic

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EnrichmentAgent')

load_dotenv()

def get_db_connection():
    """Get database connection"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not set in environment")
    return psycopg2.connect(db_url)

def create_enrichment_prompt(job: Dict[str, Any]) -> str:
    """Create prompt for Claude to extract metadata"""
    
    return f"""You are an expert HR data analyst. Your task is to extract structured metadata from a job description to match an existing data schema.

JOB DETAILS:
Title: {job.get('title', 'Not specified')}
Company: {job.get('company', 'Not specified')}
Location: {job.get('location', 'Not specified')}

DESCRIPTION:
{job.get('description', '')[:10000]}

REQUIRED OUTPUT SCHEMA (JSON):
{{
    "ai_employment_type": ["FULL_TIME" | "PART_TIME" | "CONTRACT" | "INTERN" | "FREELANCE"],
    "ai_work_arrangement": "On-site" | "Hybrid" | "Remote",
    "ai_experience_level": "Student" | "Entry Level" | "Mid Level" | "Senior" | "Lead" | "Executive",
    "ai_job_language": "de" | "en" | "fr" | "other",
    "ai_key_skills": ["skill1", "skill2", ...],  // Extract 5-15 top technical and soft skills
    "ai_keywords": ["keyword1", "keyword2", ...], // Broader keywords for search
    "ai_competencies": ["Competency1", "Competency2", ...], // Abstract capabilities from RESPONSIBILITIES
    "ai_core_responsibilities": "Summary of main responsibilities...",
    "ai_requirements_summary": "Summary of key requirements...",
    "ai_benefits": ["benefit1", "benefit2", ...],
    "ai_taxonomies_a": ["Industry1", "Industry2", ...], // e.g. "Technology", "Healthcare", "Marketing"
    "cities_derived": ["CityName"], // Extract city from location or description
    "lats_derived": [0.0], // Approximate latitude for the city (if known, else omit or 0.0)
    "lngs_derived": [0.0]  // Approximate longitude for the city (if known, else omit or 0.0)
}}

INSTRUCTIONS:
1. Extract ai_competencies ONLY from the "Responsibilities" / "Role" section. Look for abstract capabilities like "Stakeholder Management", "People Leadership", "System Architecture", "Budgeting", "Mentoring".
2. Extract ai_key_skills primarily from the "Requirements" section. Focus on HARD skills and Tools (e.g. "Python", "AWS", "Jira").
3. If specific info is missing, make a best educated guess based on context.
4. For lats_derived/lngs_derived, provide the coordinates of the main city center if identified.
5. Output PURE JSON only. No markdown formatting.
"""

def parse_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON response from partial or markdown-wrapped text"""
    try:
        # Strip markdown code blocks if present
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Raw text: {response_text}")
        return None

def enrich_job_row(client: Anthropic, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Enrich a single job using Claude"""
    try:
        prompt = create_enrichment_prompt(job)
        
        response = client.messages.create(
            model="claude-3-haiku-20240307", # Using Haiku for speed and availability
            max_tokens=2000,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return parse_llm_response(response.content[0].text)
        
    except Exception as e:
        logger.error(f"Error enriching job {job.get('id')}: {e}")
        return None

def update_job_in_db(conn, job_id: int, data: Dict[str, Any]):
    """Update job row with enriched data"""
    cursor = conn.cursor()
    
    # Map dictionary keys to DB columns
    # We need to make sure we cast lists to arrays where appropriate if using psycopg2 directly,
    # but psycopg2 usually handles lists -> arrays automatically with correct adapters.
    
    query = """
        UPDATE jobs 
        SET 
            ai_employment_type = %s,
            ai_work_arrangement = %s,
            ai_experience_level = %s,
            ai_job_language = %s,
            ai_key_skills = %s,
            ai_keywords = %s,
            ai_competencies = %s,
            ai_core_responsibilities = %s,
            ai_requirements_summary = %s,
            ai_benefits = %s,
            ai_taxonomies_a = %s,
            cities_derived = %s,
            lats_derived = %s,
            lngs_derived = %s,
            source_type = 'internal_enrichment_agent'
        WHERE id = %s
    """
    
    values = (
        data.get('ai_employment_type', []),
        data.get('ai_work_arrangement'),
        data.get('ai_experience_level'),
        data.get('ai_job_language'),
        data.get('ai_key_skills', []),
        list(set(data.get('ai_keywords', []) + data.get('ai_competencies', []))), # Merge competencies into keywords for backward compat
        data.get('ai_competencies', []),  # Store competencies in dedicated column
        data.get('ai_core_responsibilities'),
        data.get('ai_requirements_summary'),
        data.get('ai_benefits', []),
        data.get('ai_taxonomies_a', []),
        data.get('cities_derived', []),
        data.get('lats_derived', []),
        data.get('lngs_derived', []),
        job_id
    )
    
    cursor.execute(query, values)
    conn.commit()
    cursor.close()

def enrich_jobs(db_connection=None, limit: int = 50):
    """
    Main function to enrich missing jobs.
    Can be imported and called by cron script.
    
    Args:
        db_connection: Optional existing DB connection
        limit: Max jobs to process in one run (default 50 to avoid timeouts/rate limits)
    """
    stats = {'processed': 0, 'success': 0, 'failed': 0}
    
    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found")
        return stats

    client = Anthropic(api_key=api_key)
    
    should_close_conn = False
    if not db_connection:
        try:
            db_connection = get_db_connection()
            should_close_conn = True
        except Exception as e:
            logger.error(f"Failed to connect to DB: {e}")
            return stats

    try:
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        
        # Find candidate jobs
        # source_type IS NULL or empty string
        logger.info("Searching for unenriched jobs...")
        cursor.execute("""
            SELECT id, title, company, location, description 
            FROM jobs 
            WHERE (source_type IS NULL OR source_type = '') 
            LIMIT %s
        """, (limit,))
        
        jobs = cursor.fetchall()
        cursor.close()
        
        if not jobs:
            logger.info("No jobs found needing enrichment.")
            return stats
            
        logger.info(f"Found {len(jobs)} jobs to enrich.")
        
        for job in jobs:
            stats['processed'] += 1
            logger.info(f"Enriching job {job['id']}: {job.get('title', 'Unknown')}...")
            
            enriched_data = enrich_job_row(client, job)
            
            if enriched_data:
                try:
                    update_job_in_db(db_connection, job['id'], enriched_data)
                    stats['success'] += 1
                    logger.info("  -> Success")
                except Exception as e:
                    logger.error(f"  -> DB Update Failed: {e}")
                    stats['failed'] += 1
            else:
                logger.warning("  -> Extraction Failed")
                stats['failed'] += 1
                
    except Exception as e:
        logger.error(f"Unexpected error in enrich_jobs: {e}")
    finally:
        if should_close_conn and db_connection:
            db_connection.close()
            
    logger.info(f"Enrichment run complete. Stats: {stats}")
    return stats

if __name__ == "__main__":
    # If run directly
    enrich_jobs(limit=10)
