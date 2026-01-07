"""
Migration script to add competency_mappings column to user_job_matches table
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

def add_competency_mappings_column():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    try:
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='user_job_matches' 
            AND column_name='competency_mappings'
        """)
        
        if cur.fetchone():
            print("✓ Column 'competency_mappings' already exists")
        else:
            print("Adding 'competency_mappings' column...")
            cur.execute("""
                ALTER TABLE user_job_matches 
                ADD COLUMN competency_mappings JSONB
            """)
            conn.commit()
            print("✓ Successfully added 'competency_mappings' column")
        
        # Check if skill_mappings column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='user_job_matches' 
            AND column_name='skill_mappings'
        """)
        
        if cur.fetchone():
            print("✓ Column 'skill_mappings' already exists")
        else:
            print("Adding 'skill_mappings' column...")
            cur.execute("""
                ALTER TABLE user_job_matches 
                ADD COLUMN skill_mappings JSONB
            """)
            conn.commit()
            print("✓ Successfully added 'skill_mappings' column")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_competency_mappings_column()
