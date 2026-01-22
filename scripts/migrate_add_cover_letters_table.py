#!/usr/bin/env python3
"""
Migration: Add cover_letters table

Creates a table to store generated cover letters similar to resumes.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def migrate():
    """Create cover_letters table"""

    DATABASE_URL = os.getenv('DATABASE_URL')

    if not DATABASE_URL or not DATABASE_URL.startswith('postgres'):
        print("❌ Error: DATABASE_URL not set or not PostgreSQL")
        print("This migration is for PostgreSQL only")
        return False

    print(f"🔗 Connecting to database...")
    print(f"   URL: {DATABASE_URL[:50]}...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("\n📊 Creating cover_letters table...")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cover_letters (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                job_id INTEGER NOT NULL,
                job_title TEXT NOT NULL,
                job_company TEXT NOT NULL,
                cover_letter_html TEXT NOT NULL,
                cover_letter_pdf_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, job_id)
            );
        """)

        print("   ✅ Created cover_letters table")

        # Create index for faster lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cover_letters_user_id
            ON cover_letters(user_id);
        """)

        print("   ✅ Created index on user_id")

        conn.commit()

        print("\n✅ Migration completed successfully!")
        print("\nTable structure:")
        print("  • id - Primary key")
        print("  • user_id - Foreign key to users table")
        print("  • job_id - Job ID")
        print("  • job_title - Job title")
        print("  • job_company - Company name")
        print("  • cover_letter_html - HTML content")
        print("  • cover_letter_pdf_path - PDF file path (optional)")
        print("  • created_at - Timestamp")

        cur.close()
        conn.close()

        return True

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        print(traceback.format_exc())
        if 'conn' in locals():
            conn.rollback()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Add Cover Letters Table")
    print("=" * 60)

    success = migrate()

    if success:
        print("\n" + "=" * 60)
        print("✅ Migration successful!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Migration failed!")
        print("=" * 60)
        sys.exit(1)
