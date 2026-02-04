#!/usr/bin/env python3
"""
Migration: Create skill_canonical_map table

Stores the mapping from every observed variant (lowercased) of a skill or
competency term to its display-ready canonical form.  Populated in three
waves:

    static     – hand-curated entries from skill_normalizer.py (confidence 1.0)
    embedding  – one-time clustering via paraphrase-multilingual-MiniLM-L12-v2
    auto       – daily cron discovers new terms and maps them to existing
                 canonicals (or promotes them to new canonicals)

All writers use ON CONFLICT (variant) DO NOTHING so that earlier, higher-
confidence mappings are never overwritten.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2


def run_migration():
    """Create skill_canonical_map table and index"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    try:
        cursor = conn.cursor()

        print("=" * 70)
        print("SKILL CANONICAL MAP MIGRATION")
        print("=" * 70)
        print()

        # Create table
        print("Step 1: Creating skill_canonical_map table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_canonical_map (
                variant    TEXT PRIMARY KEY,
                canonical  TEXT NOT NULL,
                confidence FLOAT DEFAULT 0.0,
                source     TEXT NOT NULL DEFAULT 'static',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        print("   Created table")

        # Create index on canonical for fast reverse-lookups
        print("Step 2: Creating index on canonical column...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_canonical_map_canonical
            ON skill_canonical_map (canonical);
        """)
        conn.commit()
        print("   Created index")
        print()

        # Verify
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'skill_canonical_map'
            ORDER BY ordinal_position
        """)
        cols = cursor.fetchall()
        print("Table columns:")
        for name, dtype in cols:
            print(f"   {name}: {dtype}")
        print()

        cursor.execute("SELECT COUNT(*) FROM skill_canonical_map")
        row_count = cursor.fetchone()[0]
        print(f"Rows in table: {row_count}")
        print()
        print("=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("   python scripts/enrich_canonical_map.py --threshold 0.75")
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
