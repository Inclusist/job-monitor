#!/usr/bin/env python3
"""
Migration: Add competency_mappings and skill_mappings to user_job_matches

These JSON columns store the detailed semantic mappings from Claude analysis:
- competency_mappings: List of {job_requirement, user_strength, match_confidence, explanation}
- skill_mappings: List of {job_skill, user_skill, match_confidence, explanation}
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

def run_migration():
    """Add competency_mappings and skill_mappings columns"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    try:
        cursor = conn.cursor()

        print("🔄 Adding competency_mappings and skill_mappings columns to user_job_matches...")

        # Add columns if they don't exist
        cursor.execute("""
            ALTER TABLE user_job_matches
            ADD COLUMN IF NOT EXISTS competency_mappings JSONB,
            ADD COLUMN IF NOT EXISTS skill_mappings JSONB;
        """)

        conn.commit()
        print("✅ Migration complete!")
        print("   - competency_mappings column added")
        print("   - skill_mappings column added")

        # Show sample of existing data to verify
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(competency_mappings) as with_comp_mappings,
                   COUNT(skill_mappings) as with_skill_mappings
            FROM user_job_matches
            WHERE claude_score IS NOT NULL
        """)
        row = cursor.fetchone()
        print(f"\n📊 Current state:")
        print(f"   Total Claude-analyzed matches: {row[0]}")
        print(f"   With competency mappings: {row[1]}")
        print(f"   With skill mappings: {row[2]}")

        if row[1] == 0:
            print(f"\n⚠️  NOTE: Existing matches don't have mappings yet.")
            print(f"   Run a new job search to populate these fields.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
