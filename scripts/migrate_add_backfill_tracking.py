#!/usr/bin/env python3
"""
Migration: Add backfill tracking table

Tracks which query combinations have been backfilled to avoid re-fetching
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database


def migrate():
    """Add backfill_tracking table"""
    print("=" * 60)
    print("MIGRATION: Add backfill tracking table")
    print("=" * 60)

    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'backfill_tracking'
            )
        """)

        if cursor.fetchone()[0]:
            print("\n✓ backfill_tracking table already exists.")
            return

        print("\n📝 Creating backfill_tracking table...")

        # Create table to track backfilled combinations
        cursor.execute("""
            CREATE TABLE backfill_tracking (
                id SERIAL PRIMARY KEY,

                -- The unique combination that was backfilled
                title_keyword TEXT,
                location TEXT,
                ai_work_arrangement TEXT,
                ai_employment_type TEXT,
                ai_seniority TEXT,
                ai_industry TEXT,

                -- Tracking
                backfilled_date TIMESTAMP DEFAULT NOW(),
                jobs_found INTEGER DEFAULT 0,

                -- Prevent duplicate backfills
                UNIQUE(title_keyword, location, ai_work_arrangement,
                       ai_employment_type, ai_seniority, ai_industry)
            )
        """)

        # Create index for lookups
        cursor.execute("""
            CREATE INDEX idx_backfill_combination ON backfill_tracking(
                title_keyword, location, ai_work_arrangement, ai_seniority
            );
        """)

        conn.commit()

        print("\n✅ Migration completed successfully!")
        print("\nTable structure:")
        print("  • Tracks which combinations have been backfilled")
        print("  • Prevents duplicate backfill API calls")
        print("  • Stores backfill date and job count")

        print("\nExample:")
        print("  User 1 signs up → Wants 'data scientist' in 'Berlin'")
        print("  → Backfill runs, adds to tracking table")
        print("\n  User 2 signs up → Also wants 'data scientist' in 'Berlin'")
        print("  → Check tracking table → Already backfilled → SKIP!")
        print("  → Saves API quota!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise

    finally:
        db._return_connection(conn)


if __name__ == "__main__":
    migrate()
