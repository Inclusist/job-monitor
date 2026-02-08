
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def backfill_competencies():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not found")
        return

    conn = None
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        logger.info("Fetching profiles with missing competencies...")
        
        # Select profiles where competencies is NULL or empty array
        cursor.execute("""
            SELECT id, raw_analysis 
            FROM cv_profiles 
            WHERE (competencies IS NULL OR competencies = '[]'::jsonb)
              AND raw_analysis IS NOT NULL
        """)
        
        profiles = cursor.fetchall()
        logger.info(f"Found {len(profiles)} profiles to backfill.")

        updated_count = 0
        for profile in profiles:
            try:
                raw = profile['raw_analysis']
                if isinstance(raw, str):
                    raw_data = json.loads(raw)
                    # Handle double-encoded string
                    if isinstance(raw_data, str):
                        try:
                            raw_data = json.loads(raw_data)
                        except:
                            pass
                elif isinstance(raw, dict):
                    raw_data = raw
                else:
                    continue

                if isinstance(raw_data, dict):
                    competencies = raw_data.get('competencies', [])
                    if competencies:
                        cursor.execute("""
                            UPDATE cv_profiles 
                            SET competencies = %s 
                            WHERE id = %s
                        """, (json.dumps(competencies), profile['id']))
                        updated_count += 1
                        logger.info(f"Updated Profile {profile['id']} with {len(competencies)} competencies.")
            except Exception as e:
                logger.error(f"Error processing profile {profile['id']}: {e}")

        logger.info(f"Backfill complete. Updated {updated_count} profiles.")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    backfill_competencies()
