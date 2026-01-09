#!/usr/bin/env python3
"""
Database Migration: Add Embedding Storage Columns

Adds columns to store pre-computed job title embeddings for fast semantic search.

Usage:
    python scripts/migrations/add_embedding_columns.py --dry-run  # Preview changes
    python scripts/migrations/add_embedding_columns.py            # Apply migration
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.factory import get_database
import argparse


def run_migration(dry_run=False, auto_yes=False):
    """Add embedding storage columns to jobs table"""

    print("\n" + "="*60)
    print("DATABASE MIGRATION: Add Embedding Columns")
    print("="*60)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️  PRODUCTION MODE - Database will be modified")

    print("\nMigration Details:")
    print("  • Add column: embedding_jobbert_title (JSONB)")
    print("  • Add column: embedding_model (VARCHAR)")
    print("  • Add column: embedding_date (TIMESTAMP)")
    print("\nPurpose:")
    print("  • Store pre-computed title embeddings for 80x faster semantic search")
    print("  • Model: TechWolf/JobBERT-v3 (768-dimensional vectors)")
    print("  • Storage: ~3KB per job, ~15MB for 5000 jobs")
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
        # Check if columns already exist
        print("\n📋 Checking current schema...")

        if is_postgres:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'jobs'
                AND column_name IN ('embedding_jobbert_title', 'embedding_model', 'embedding_date')
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
        else:
            # SQLite
            cursor.execute("PRAGMA table_info(jobs)")
            all_columns = [row[1] for row in cursor.fetchall()]
            existing_columns = [col for col in all_columns
                              if col in ('embedding_jobbert_title', 'embedding_model', 'embedding_date')]

        if existing_columns:
            print(f"⚠️  Found existing columns: {', '.join(existing_columns)}")
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
            -- Add embedding storage columns
            ALTER TABLE jobs
            ADD COLUMN IF NOT EXISTS embedding_jobbert_title JSONB,
            ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'TechWolf/JobBERT-v3',
            ADD COLUMN IF NOT EXISTS embedding_date TIMESTAMP;

            -- Add index for queries filtering on embedding existence
            CREATE INDEX IF NOT EXISTS idx_jobs_embedding_exists
            ON jobs ((embedding_jobbert_title IS NOT NULL));

            -- Add comment for documentation
            COMMENT ON COLUMN jobs.embedding_jobbert_title IS
            'Pre-computed title embedding (768-dim vector from TechWolf/JobBERT-v3) for fast semantic search';
            """
        else:
            # SQLite doesn't support ADD COLUMN IF NOT EXISTS in a single statement
            # We'll check and add one by one
            migration_sql = None
            columns_to_add = []

            if 'embedding_jobbert_title' not in existing_columns:
                columns_to_add.append(("embedding_jobbert_title", "ALTER TABLE jobs ADD COLUMN embedding_jobbert_title TEXT"))
            if 'embedding_model' not in existing_columns:
                columns_to_add.append(("embedding_model", "ALTER TABLE jobs ADD COLUMN embedding_model TEXT DEFAULT 'TechWolf/JobBERT-v3'"))
            if 'embedding_date' not in existing_columns:
                columns_to_add.append(("embedding_date", "ALTER TABLE jobs ADD COLUMN embedding_date TIMESTAMP"))

        print("\n📝 SQL to execute:")
        print("-" * 60)
        if is_postgres:
            print(migration_sql)
        else:
            if columns_to_add:
                for col_name, sql in columns_to_add:
                    print(f"{sql};")
            else:
                print("-- No columns to add (already exist)")
        print("-" * 60)

        if dry_run:
            print("\n✅ DRY RUN COMPLETE - No changes made")
            print("💡 Run without --dry-run to apply migration")
            return True

        # Execute migration
        print("\n⚙️  Executing migration...")
        if is_postgres:
            cursor.execute(migration_sql)
            conn.commit()
        else:
            # SQLite: Execute each ALTER TABLE separately
            if columns_to_add:
                for col_name, sql in columns_to_add:
                    print(f"  Adding column: {col_name}")
                    cursor.execute(sql)
                conn.commit()
                print(f"  ✓ Added {len(columns_to_add)} column(s)")
            else:
                print("  ℹ️  No columns to add (already exist)")

        # Verify columns were added
        print("\n✅ Migration executed successfully")
        print("\n🔍 Verifying new columns...")

        if is_postgres:
            cursor.execute("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'jobs'
                AND column_name IN ('embedding_jobbert_title', 'embedding_model', 'embedding_date')
                ORDER BY column_name
            """)

            print("\n📊 New Columns:")
            for row in cursor.fetchall():
                col_name, data_type, default = row
                default_str = f" (default: {default})" if default else ""
                print(f"  ✓ {col_name}: {data_type}{default_str}")

            # Check index
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'jobs'
                AND indexname = 'idx_jobs_embedding_exists'
            """)
            if cursor.fetchone():
                print("  ✓ Index: idx_jobs_embedding_exists")
        else:
            # SQLite verification
            cursor.execute("PRAGMA table_info(jobs)")
            print("\n📊 New Columns:")
            for row in cursor.fetchall():
                col_name = row[1]
                col_type = row[2]
                col_default = row[4]
                if col_name in ('embedding_jobbert_title', 'embedding_model', 'embedding_date'):
                    default_str = f" (default: {col_default})" if col_default else ""
                    print(f"  ✓ {col_name}: {col_type}{default_str}")

        # Get job count
        cursor.execute("SELECT COUNT(*) FROM jobs")
        job_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE embedding_jobbert_title IS NOT NULL")
        encoded_count = cursor.fetchone()[0]

        print(f"\n📈 Database Status:")
        print(f"  • Total jobs: {job_count:,}")
        print(f"  • Jobs with embeddings: {encoded_count:,}")
        print(f"  • Jobs needing encoding: {job_count - encoded_count:,}")

        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETE")
        print("="*60)
        print("\n💡 Next Steps:")
        print("  1. Run: python scripts/encode_existing_jobs.py")
        print("  2. Update daily cron to encode new jobs")
        print("  3. Update matcher to use pre-encoded embeddings")
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
        description='Add embedding storage columns to jobs table',
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
