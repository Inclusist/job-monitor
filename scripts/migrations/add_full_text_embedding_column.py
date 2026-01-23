#!/usr/bin/env python3
"""
Database Migration: Add Full Text Embedding Column

Adds a column to store pre-computed job full-text embeddings for semantic search.

Usage:
    python scripts/migrations/add_full_text_embedding_column.py --dry-run
    python scripts/migrations/add_full_text_embedding_column.py
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
    """Add full text embedding storage column to jobs table"""

    print("\n" + "="*60)
    print("DATABASE MIGRATION: Add Full Text Embedding Column")
    print("="*60)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️  PRODUCTION MODE - Database will be modified")

    print("\nMigration Details:")
    print("  • Add column: embedding_jobbert_full (JSONB)")
    print("\nPurpose:")
    print("  • Store pre-computed full-text embeddings for semantic search.")
    print("  • Model: TechWolf/JobBERT-v3 (768-dimensional vectors)")
    print("\n" + "="*60)

    if not dry_run and not auto_yes:
        response = input("\n⚠️  Proceed with migration? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            return False
    elif not dry_run and auto_yes:
        print("\n✅ Auto-confirmed: Proceeding with migration")

    # Connect to database
    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Detect database type
    is_postgres = hasattr(db, 'connection_pool') or os.getenv('DATABASE_URL', '').startswith('postgres')
    db_type = "PostgreSQL" if is_postgres else "SQLite"
    print(f"\n🔍 Detected database: {db_type}")

    try:
        # Check if column already exists
        print("\n📋 Checking current schema...")

        if is_postgres:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'jobs'
                AND column_name = 'embedding_jobbert_full'
            """ )
            existing_columns = [row[0] for row in cursor.fetchall()]
        else:
            # SQLite
            cursor.execute("PRAGMA table_info(jobs)")
            all_columns = [row[1] for row in cursor.fetchall()]
            existing_columns = [col for col in all_columns if col == 'embedding_jobbert_full']

        if existing_columns:
            print(f"⚠️  Found existing column: embedding_jobbert_full")
            print("   Migration may have already been applied")

            if not dry_run and not auto_yes:
                response = input("   Continue anyway? (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Migration cancelled")
                    return False
            elif not dry_run and auto_yes:
                print("   ✅ Auto-confirmed: Continuing")

        # SQL migration (database-specific)
        if is_postgres:
            migration_sql = """
            -- Add full text embedding storage column
            ALTER TABLE jobs
            ADD COLUMN IF NOT EXISTS embedding_jobbert_full JSONB;

            -- Add comment for documentation
            COMMENT ON COLUMN jobs.embedding_jobbert_full IS
            'Pre-computed full-text embedding (768-dim vector from TechWolf/JobBERT-v3) for semantic search';
            """
        else:
            # SQLite
            migration_sql = None
            if 'embedding_jobbert_full' not in existing_columns:
                migration_sql = "ALTER TABLE jobs ADD COLUMN embedding_jobbert_full TEXT"

        print("\n📝 SQL to execute:")
        print("-" * 60)
        if migration_sql:
            print(f"{migration_sql};")
        else:
            print("-- No column to add (already exists)")
        print("-" * 60)

        if dry_run:
            print("\n✅ DRY RUN COMPLETE - No changes made")
            print("💡 Run without --dry-run to apply migration")
            return True

        # Execute migration
        print("\n⚙️  Executing migration...")
        if migration_sql:
            cursor.execute(migration_sql)
            conn.commit()
        else:
            print("  ℹ️  No column to add (already exists)")

        # Verify column was added
        print("\n✅ Migration executed successfully")
        print("\n🔍 Verifying new column...")

        if is_postgres:
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'jobs'
                AND column_name = 'embedding_jobbert_full'
            """ )
            row = cursor.fetchone()
            if row:
                col_name, data_type = row
                print(f"  ✓ {col_name}: {data_type}")
        else:
            # SQLite verification
            cursor.execute("PRAGMA table_info(jobs)")
            for row in cursor.fetchall():
                col_name = row[1]
                col_type = row[2]
                if col_name == 'embedding_jobbert_full':
                    print(f"  ✓ {col_name}: {col_type}")
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETE")
        print("="*60)
        print("\n💡 Next Steps:")
        print("  1. Run: python scripts/backfill_full_text_embeddings.py")
        print("\n")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run:
            conn.rollback()
            print("🔄 Changes rolled back")
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
        description='Add full text embedding column to jobs table',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying database'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Auto-confirm migration (skip prompts)'
    )

    args = parser.parse_args()

    try:
        success = run_migration(dry_run=args.dry_run, auto_yes=args.yes)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)


if __name__ == '__main__':
    main()
