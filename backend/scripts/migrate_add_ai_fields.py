#!/usr/bin/env python3
"""
Migration: Add AI-extracted fields to jobs table

Adds columns for AI-extracted metadata from Active Jobs DB:
- ai_employment_type: Full-time, Part-time, Contract, etc.
- ai_work_arrangement: Remote, Hybrid, Onsite
- ai_seniority: Entry, Mid, Senior, Lead, etc.
- ai_industry: Technology, Finance, Healthcare, etc.

These fields enable better job matching against user preferences.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database


def migrate():
    """Add AI-extracted fields to jobs table"""
    print("=" * 60)
    print("MIGRATION: Add AI-extracted fields to jobs table")
    print("=" * 60)

    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'jobs'
            AND column_name IN ('ai_employment_type', 'ai_work_arrangement', 'ai_seniority', 'ai_industry')
        """)

        existing_columns = [row[0] for row in cursor.fetchall()]

        if len(existing_columns) == 4:
            print("\n✓ All AI fields already exist. No migration needed.")
            db._return_connection(conn)
            return

        if existing_columns:
            print(f"\n⚠️  Some AI fields already exist: {existing_columns}")
            print("   Adding missing fields...")

        # Add new columns
        print("\n📝 Adding AI-extracted metadata columns to jobs table...")

        columns_to_add = {
            'ai_employment_type': 'AI-extracted employment type (Full-time, Part-time, Contract, etc.)',
            'ai_work_arrangement': 'AI-extracted work arrangement (Remote, Hybrid, Onsite)',
            'ai_seniority': 'AI-extracted seniority level (Entry, Mid, Senior, Lead, etc.)',
            'ai_industry': 'AI-extracted industry (Technology, Finance, Healthcare, etc.)'
        }

        for column_name, description in columns_to_add.items():
            if column_name not in existing_columns:
                print(f"\n  Adding: {column_name}")
                print(f"    Description: {description}")

                cursor.execute(f"""
                    ALTER TABLE jobs
                    ADD COLUMN IF NOT EXISTS {column_name} TEXT
                """)

                print(f"    ✓ Added {column_name}")

        conn.commit()

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)

        print("\nNew AI fields available:")
        print("  • ai_employment_type - Employment type classification")
        print("  • ai_work_arrangement - Work arrangement (remote/hybrid/onsite)")
        print("  • ai_seniority - Seniority level")
        print("  • ai_industry - Industry classification")

        print("\nThese fields will be:")
        print("  1. Automatically populated from Active Jobs DB API")
        print("  2. Used by Claude for better job matching")
        print("  3. Matched against user's work_arrangement_preference from CV")

        # Show table schema
        print("\n📊 Updated jobs table schema:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'jobs'
            ORDER BY ordinal_position
        """)

        for row in cursor.fetchall():
            col_name, col_type = row
            marker = " [NEW]" if col_name in columns_to_add else ""
            print(f"  {col_name}: {col_type}{marker}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise

    finally:
        db._return_connection(conn)


if __name__ == "__main__":
    migrate()
