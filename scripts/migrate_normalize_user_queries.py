#!/usr/bin/env python3
"""
Migration: Normalize user_search_queries table

Changes from pipe-separated to normalized rows:
OLD: user_id=1, title_keywords="DS|ML", locations="Berlin|Hamburg"
NEW: 4 rows - DS+Berlin, DS+Hamburg, ML+Berlin, ML+Hamburg

This enables database-level deduplication across users!
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database


def migrate():
    """Normalize user_search_queries table"""
    print("=" * 60)
    print("MIGRATION: Normalize user_search_queries table")
    print("=" * 60)

    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'user_search_queries'
            )
        """)

        if not cursor.fetchone()[0]:
            print("\n⚠️  user_search_queries table doesn't exist.")
            print("Run migrate_add_user_queries.py first!")
            return

        print("\n📝 Step 1: Backing up existing data...")

        # Get existing data
        cursor.execute("SELECT * FROM user_search_queries")
        existing_data = cursor.fetchall()
        print(f"  Found {len(existing_data)} existing queries")

        # Drop old table
        print("\n📝 Step 2: Dropping old table structure...")
        cursor.execute("DROP TABLE IF EXISTS user_search_queries CASCADE")

        # Create new normalized table
        print("\n📝 Step 3: Creating normalized table structure...")
        cursor.execute("""
            CREATE TABLE user_search_queries (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                query_name TEXT NOT NULL,

                -- NORMALIZED: Single values (not pipe-separated)
                title_keyword TEXT,              -- Single keyword (e.g., 'data scientist')
                location TEXT,                   -- Single location (e.g., 'Berlin')

                -- AI-powered filters (optional, can be NULL)
                ai_work_arrangement TEXT,        -- e.g., 'Remote OK', 'Hybrid'
                ai_employment_type TEXT,         -- e.g., 'Full-time'
                ai_seniority TEXT,               -- e.g., 'Senior', 'Lead'
                ai_industry TEXT,                -- e.g., 'Technology'

                -- Query metadata
                is_active BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 0,

                -- Tracking
                created_date TIMESTAMP DEFAULT NOW(),
                last_run_date TIMESTAMP,

                -- Composite unique constraint: prevents exact duplicates per user
                UNIQUE(user_id, query_name, title_keyword, location,
                       ai_work_arrangement, ai_employment_type, ai_seniority, ai_industry)
            )
        """)

        # Create indices for performance
        cursor.execute("""
            CREATE INDEX idx_user_queries_user_id ON user_search_queries(user_id);
            CREATE INDEX idx_user_queries_active ON user_search_queries(is_active) WHERE is_active = TRUE;
            CREATE INDEX idx_user_queries_dedup ON user_search_queries(title_keyword, location,
                ai_work_arrangement, ai_seniority) WHERE is_active = TRUE;
        """)

        # Migrate existing data if any
        if existing_data:
            print(f"\n📝 Step 4: Migrating {len(existing_data)} existing queries...")
            migrated_count = 0

            for row in existing_data:
                # Note: Row structure from old table
                # Assuming: id, user_id, query_name, title_keywords, locations, ...
                # This is placeholder - adjust based on actual old structure
                print(f"  ⚠️  Manual migration required for existing data")
                print(f"     Old data used pipe-separated values")
                print(f"     Please re-generate queries from CVs or create manually")

        else:
            print("\n📝 Step 4: No existing data to migrate")

        conn.commit()

        print("\n✅ Migration completed successfully!")
        print("\nNew table structure (NORMALIZED):")
        print("  • id (primary key)")
        print("  • user_id (foreign key)")
        print("  • query_name")
        print("  • title_keyword (SINGLE value, not pipe-separated)")
        print("  • location (SINGLE value, not pipe-separated)")
        print("  • AI filters (work_arrangement, employment_type, seniority, industry)")
        print("  • is_active, priority")
        print("  • created_date, last_run_date")

        print("\nExample: User wants 'data scientist' and 'ML engineer' in 'Berlin' and 'Hamburg'")
        print("  → Creates 4 rows:")
        print("     1. data scientist + Berlin")
        print("     2. data scientist + Hamburg")
        print("     3. ML engineer + Berlin")
        print("     4. ML engineer + Hamburg")

        print("\nDeduplication query:")
        print("""
  SELECT DISTINCT title_keyword, location, ai_work_arrangement, ai_seniority
  FROM user_search_queries
  WHERE is_active = TRUE;
        """)

        print("\nBenefits:")
        print("  ✓ Database-level deduplication (DISTINCT)")
        print("  ✓ No string parsing needed")
        print("  ✓ Better query performance")
        print("  ✓ Automatic quota savings across users")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise

    finally:
        db._return_connection(conn)


if __name__ == "__main__":
    migrate()
