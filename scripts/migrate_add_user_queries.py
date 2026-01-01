#!/usr/bin/env python3
"""
Migration: Add user_search_queries table

Enables per-user personalized job search queries using Active Jobs DB's
concatenation operators (e.g., 'data scientist'|'ML engineer', Berlin|Hamburg)
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database


def migrate():
    """Add user_search_queries table"""
    print("=" * 60)
    print("MIGRATION: Add user_search_queries table")
    print("=" * 60)

    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    try:
        # Check if table already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'user_search_queries'
            )
        """)

        if cursor.fetchone()[0]:
            print("\n✓ user_search_queries table already exists. No migration needed.")
            db._return_connection(conn)
            return

        print("\n📝 Creating user_search_queries table...")

        # Create table
        cursor.execute("""
            CREATE TABLE user_search_queries (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                query_name TEXT NOT NULL,

                -- Search parameters using Active Jobs DB pipe (|) operator
                title_keywords TEXT,              -- e.g., 'data scientist|ML engineer|AI engineer'
                locations TEXT,                   -- e.g., 'Berlin|Hamburg|Munich'

                -- AI-powered filters (optional)
                ai_work_arrangement TEXT,         -- e.g., 'Remote OK|Hybrid'
                ai_employment_type TEXT,          -- e.g., 'Full-time'
                ai_seniority TEXT,                -- e.g., 'Senior|Lead'
                ai_industry TEXT,                 -- e.g., 'Technology|Finance'

                -- Query metadata
                is_active BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 0,       -- Higher priority queries run first
                max_results INTEGER DEFAULT 100,  -- Max results per query

                -- Tracking
                created_date TIMESTAMP DEFAULT NOW(),
                last_run_date TIMESTAMP,
                last_job_count INTEGER DEFAULT 0,

                -- Ensure unique query names per user
                UNIQUE(user_id, query_name)
            )
        """)

        # Create indices for performance
        cursor.execute("""
            CREATE INDEX idx_user_queries_user_id ON user_search_queries(user_id);
            CREATE INDEX idx_user_queries_active ON user_search_queries(is_active) WHERE is_active = TRUE;
        """)

        conn.commit()

        print("\n✅ Migration completed successfully!")
        print("\nTable structure:")
        print("  • id (primary key)")
        print("  • user_id (foreign key to users)")
        print("  • query_name (e.g., 'Primary Search', 'Backup Jobs')")
        print("  • title_keywords (pipe-separated: 'keyword1|keyword2|keyword3')")
        print("  • locations (pipe-separated: 'Berlin|Hamburg|Munich')")
        print("  • ai_work_arrangement, ai_employment_type, ai_seniority, ai_industry")
        print("  • is_active, priority, max_results")
        print("  • created_date, last_run_date, last_job_count")

        print("\nExample query:")
        print("""
        INSERT INTO user_search_queries (user_id, query_name, title_keywords, locations, ai_work_arrangement)
        VALUES (1, 'Primary Search', 'data scientist|ML engineer', 'Berlin|Hamburg', 'Remote OK|Hybrid');
        """)

        print("\nActive Jobs DB will search:")
        print("  Titles: 'data scientist' OR 'ML engineer'")
        print("  Locations: Berlin OR Hamburg")
        print("  Work: Remote OK OR Hybrid")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise

    finally:
        db._return_connection(conn)


if __name__ == "__main__":
    migrate()
