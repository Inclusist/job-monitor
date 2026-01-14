#!/usr/bin/env python3
"""
Migration: Add resume generation support

This migration adds:
1. user_claimed_competencies (JSONB) to cv_profiles - stores competencies user claims with evidence
2. user_claimed_skills (JSONB) to cv_profiles - stores skills user claims with evidence
3. user_generated_resumes table - stores generated resume HTML and PDF paths

Schema for claimed competencies/skills:
{
  "Agile Methodology": {
    "work_experience_ids": [1, 3],
    "evidence": "Led daily standups and sprint planning for 5-person team",
    "added_at": "2026-01-14T10:30:00Z"
  },
  ...
}
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

def run_migration():
    """Add resume generation columns and table"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    try:
        cursor = conn.cursor()

        print("=" * 70)
        print("🔄 RESUME GENERATION MIGRATION")
        print("=" * 70)
        print()

        # Step 1: Add columns to cv_profiles
        print("📋 Step 1: Adding columns to cv_profiles table...")
        cursor.execute("""
            ALTER TABLE cv_profiles
            ADD COLUMN IF NOT EXISTS user_claimed_competencies JSONB DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS user_claimed_skills JSONB DEFAULT '{}';
        """)
        conn.commit()
        print("   ✅ user_claimed_competencies column added")
        print("   ✅ user_claimed_skills column added")
        print()

        # Step 2: Create user_generated_resumes table
        print("📋 Step 2: Creating user_generated_resumes table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_generated_resumes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                resume_html TEXT NOT NULL,
                resume_pdf_path TEXT,
                selections_used JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        print("   ✅ user_generated_resumes table created")
        print()

        # Step 3: Add indexes
        print("📋 Step 3: Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_resumes_user_job
            ON user_generated_resumes(user_id, job_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_resumes_created
            ON user_generated_resumes(created_at DESC);
        """)
        conn.commit()
        print("   ✅ idx_user_resumes_user_job created")
        print("   ✅ idx_user_resumes_created created")
        print()

        # Step 4: Verify migration
        print("=" * 70)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 70)
        print()

        # Check cv_profiles
        cursor.execute("""
            SELECT COUNT(*) as total_profiles,
                   COUNT(CASE WHEN user_claimed_competencies::text != '{}' THEN 1 END) as with_claimed_comp,
                   COUNT(CASE WHEN user_claimed_skills::text != '{}' THEN 1 END) as with_claimed_skills
            FROM cv_profiles
        """)
        row = cursor.fetchone()
        print("📊 CV Profiles Status:")
        print(f"   Total profiles: {row[0]}")
        print(f"   With claimed competencies: {row[1]}")
        print(f"   With claimed skills: {row[2]}")
        print()

        # Check user_generated_resumes
        cursor.execute("""
            SELECT COUNT(*) as total_resumes
            FROM user_generated_resumes
        """)
        row = cursor.fetchone()
        print("📊 Generated Resumes Status:")
        print(f"   Total resumes: {row[0]}")
        print()

        # Show table structure
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'user_generated_resumes'
            ORDER BY ordinal_position
        """)
        print("📊 Table Structure: user_generated_resumes")
        for col in cursor.fetchall():
            print(f"   - {col[0]} ({col[1]})")
        print()

        print("✅ Ready for resume generation feature!")
        print()
        print("Next steps:")
        print("   1. Implement PostgresResumeOperations class")
        print("   2. Implement ResumeGenerator class")
        print("   3. Add API endpoints for evidence collection and generation")
        print("   4. Update frontend to make competency/skill boxes clickable")
        print()

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        import traceback
        print(traceback.format_exc())
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
