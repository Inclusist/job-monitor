
import os
import psycopg2
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def migrate_db():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return

    conn = None
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()

        logger.info("Checking if 'competencies' column exists in 'cv_profiles'...")
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='cv_profiles' AND column_name='competencies';
        """)
        
        if cursor.fetchone():
            logger.info("Column 'competencies' already exists. Skipping.")
        else:
            logger.info("Adding 'competencies' column to 'cv_profiles'...")
            cursor.execute("""
                ALTER TABLE cv_profiles 
                ADD COLUMN competencies JSONB DEFAULT '[]'::jsonb;
            """)
            logger.info("Successfully added 'competencies' column.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_db()
