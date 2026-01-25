#!/usr/bin/env python3
"""
Database Migration: Add User Job Skill Claims Table

Adds a table to store user-claimed skills for a specific job application.

Usage:
    python scripts/migrations/add_user_job_skill_claims_table.py --dry-run
    python scripts/migrations/add_user_job_skill_claims_table.py
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.factory import get_database
import argparse


def run_migration(dry_run=False, auto_yes=False):
    """Add user_job_skill_claims table"""

    print("\n" + "="*60)
    print("DATABASE MIGRATION: Add user_job_skill_claims Table")
    print("="*60)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️  PRODUCTION MODE - Database will be modified")

    print("\nMigration Details:")
    print("  • Create table: user_job_skill_claims")
    print("\nPurpose:")
    print("  • Store user-claimed skills and competencies for a specific job application, to be used in tailored resume and cover letter generation.")
    print("\n" + "="*60)

    if not dry_run and not auto_yes:
        response = input("\n⚠️  Proceed with migration? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            return False
    elif not dry_run and auto_yes:
        print("\n✅ Auto-confirmed: Proceeding with migration")

    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    is_postgres = hasattr(db, 'connection_pool') or os.getenv('DATABASE_URL', '').startswith('postgres')
    db_type = "PostgreSQL" if is_postgres else "SQLite"
    print(f"\n🔍 Detected database: {db_type}")

    try:
        if is_postgres:
            migration_sql = """
            CREATE TABLE IF NOT EXISTS user_job_skill_claims (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                skill_type TEXT NOT NULL, -- 'competency' or 'skill'
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE (user_id, job_id, skill_name)
            );
            """
        else:
            migration_sql = """
            CREATE TABLE IF NOT EXISTS user_job_skill_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                skill_type TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE (user_id, job_id, skill_name)
            );
            """

        print("\n📝 SQL to execute:")
        print("-" * 60)
        print(migration_sql)
        print("-" * 60)

        if dry_run:
            print("\n✅ DRY RUN COMPLETE - No changes made")
            return True

        print("\n⚙️  Executing migration...")
        cursor.execute(migration_sql)
        conn.commit()

        print("\n✅ MIGRATION COMPLETE")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        if hasattr(db, '_return_connection'):
            db._return_connection(conn)
        else:
            conn.close()
        db.close()

def main():
    parser = argparse.ArgumentParser(
        description='Add user_job_skill_claims table.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying database')
    parser.add_argument('--yes', action='store_true', help='Auto-confirm migration')
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run, auto_yes=args.yes)

if __name__ == '__main__':
    main()
