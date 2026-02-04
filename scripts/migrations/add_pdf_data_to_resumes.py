#!/usr/bin/env python3
"""
Migration: Store resume PDFs as BYTEA in the database

Adds resume_pdf_data BYTEA column to user_generated_resumes.
This replaces the file-path approach (resume_pdf_path) which was
unreliable because static/resumes/ is ephemeral across deploys.

After running this migration, backfill existing resumes by running:
    python scripts/migrations/backfill_pdf_data.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2


def run_migration():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    try:
        cursor = conn.cursor()

        print("=" * 70)
        print("ADD resume_pdf_data BYTEA COLUMN")
        print("=" * 70)
        print()

        cursor.execute("""
            ALTER TABLE user_generated_resumes
            ADD COLUMN IF NOT EXISTS resume_pdf_data BYTEA;
        """)
        conn.commit()
        print("   Added resume_pdf_data column")

        # Show current state
        cursor.execute("""
            SELECT id,
                   resume_pdf_path IS NOT NULL as has_path,
                   resume_pdf_data IS NOT NULL as has_data,
                   resume_html IS NOT NULL      as has_html
            FROM user_generated_resumes
            ORDER BY id
        """)
        rows = cursor.fetchall()
        print(f"\n   Existing resumes ({len(rows)}):")
        print(f"   {'id':>4}  has_path  has_data  has_html")
        for r in rows:
            print(f"   {r[0]:>4}  {str(r[1]):>8}  {str(r[2]):>8}  {str(r[3]):>8}")

        print()
        print("=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print()
        print("Next: python scripts/migrations/backfill_pdf_data.py")
        print()

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
