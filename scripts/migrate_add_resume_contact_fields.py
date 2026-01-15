#!/usr/bin/env python3
"""
Migration: Add resume contact fields to users table

Adds:
- resume_name: TEXT (optional, falls back to name)
- resume_email: TEXT (optional, falls back to email)
- resume_phone: TEXT (optional)

These fields are separate from login credentials.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def migrate():
    """Add resume contact fields to users table"""

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

        print("\n📊 Checking current table structure...")
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)
        existing_columns = [row[0] for row in cur.fetchall()]
        print(f"   Existing columns: {', '.join(existing_columns)}")

        # Add resume_name column
        if 'resume_name' not in existing_columns:
            print("\n➕ Adding 'resume_name' column...")
            cur.execute("ALTER TABLE users ADD COLUMN resume_name TEXT;")
            print("   ✅ Added resume_name")
        else:
            print("\n✓ Column 'resume_name' already exists")

        # Add resume_email column
        if 'resume_email' not in existing_columns:
            print("➕ Adding 'resume_email' column...")
            cur.execute("ALTER TABLE users ADD COLUMN resume_email TEXT;")
            print("   ✅ Added resume_email")
        else:
            print("✓ Column 'resume_email' already exists")

        # Add resume_phone column
        if 'resume_phone' not in existing_columns:
            print("➕ Adding 'resume_phone' column...")
            cur.execute("ALTER TABLE users ADD COLUMN resume_phone TEXT;")
            print("   ✅ Added resume_phone")
        else:
            print("✓ Column 'resume_phone' already exists")

        conn.commit()

        print("\n✅ Migration completed successfully!")
        print("\nNew columns added:")
        print("  • resume_name  - Name to display on resumes (optional)")
        print("  • resume_email - Email to display on resumes (optional)")
        print("  • resume_phone - Phone number for resumes (optional)")
        print("\nThese fields are separate from login credentials.")

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
    print("Migration: Add Resume Contact Fields")
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
