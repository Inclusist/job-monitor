#!/usr/bin/env python3
"""
Migration: Add projects support to CV profiles

This migration adds:
1. projects (TEXT) to cv_profiles - stores user's project descriptions

Schema for projects:
JSON array of formatted project text blocks:
[
  "Project Name\n• Description\n• Technologies: Python, Flask",
  "Another Project\n• Description\n• Technologies: React, Node.js"
]
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

def run_migration():
    """Add projects column to cv_profiles table"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    try:
        cursor = conn.cursor()

        print("=" * 70)
        print("🔄 PROJECTS FEATURE MIGRATION")
        print("=" * 70)
        print()

        # Step 1: Add projects column to cv_profiles
        print("📋 Step 1: Adding projects column to cv_profiles table...")
        cursor.execute("""
            ALTER TABLE cv_profiles
            ADD COLUMN IF NOT EXISTS projects TEXT;
        """)
        conn.commit()
        print("   ✅ projects column added")
        print()

        # Step 2: Verify migration
        print("=" * 70)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 70)
        print()

        # Check cv_profiles
        cursor.execute("""
            SELECT COUNT(*) as total_profiles,
                   COUNT(CASE WHEN projects IS NOT NULL AND projects != '[]' THEN 1 END) as with_projects
            FROM cv_profiles
        """)
        row = cursor.fetchone()
        print("📊 CV Profiles Status:")
        print(f"   Total profiles: {row[0]}")
        print(f"   Profiles with projects: {row[1]}")
        print()

        # Show column details
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'cv_profiles' AND column_name = 'projects'
        """)
        col = cursor.fetchone()
        if col:
            print("📊 Column Details:")
            print(f"   Name: {col[0]}")
            print(f"   Type: {col[1]}")
            print(f"   Nullable: {col[2]}")
        print()

        print("✅ Ready for projects feature!")
        print()
        print("Next steps:")
        print("   1. Create ProjectFormatter service class")
        print("   2. Add API endpoints for /api/format-project and /api/save-projects")
        print("   3. Update profile.html with projects section UI")
        print("   4. Integrate projects into resume generation")
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
