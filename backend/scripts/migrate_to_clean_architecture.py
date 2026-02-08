#!/usr/bin/env python3
"""
Migrate to clean architecture:
1. Backup old jobs table (with user-specific fields mixed in)
2. Rename raw_jobs_test to jobs (pure global data)
3. Clear user_job_matches (will be repopulated)
4. Update sequences and constraints
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

def migrate():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print("=" * 80)
    print("DATABASE MIGRATION - Clean Architecture")
    print("=" * 80)

    # Step 1: Backup old jobs table
    print("\n1. Backing up old jobs table...")
    cursor.execute("DROP TABLE IF EXISTS jobs_legacy_backup CASCADE")
    cursor.execute("ALTER TABLE IF EXISTS jobs RENAME TO jobs_legacy_backup")
    print("   ✓ Old jobs table backed up to jobs_legacy_backup")

    # Step 2: Rename raw_jobs_test to jobs
    print("\n2. Promoting raw_jobs_test to jobs table...")
    cursor.execute("ALTER TABLE raw_jobs_test RENAME TO jobs")
    print("   ✓ raw_jobs_test renamed to jobs")

    # Step 3: Update the primary key constraint name
    print("\n3. Updating constraints...")
    try:
        cursor.execute("""
            ALTER TABLE jobs
            RENAME CONSTRAINT raw_jobs_test_pkey TO jobs_pkey
        """)
        print("   ✓ Primary key constraint renamed")
    except psycopg2.errors.DuplicateTable:
        print("   ✓ Primary key constraint already named correctly")
        conn.rollback()

    try:
        cursor.execute("""
            ALTER TABLE jobs
            RENAME CONSTRAINT raw_jobs_test_external_id_key TO jobs_external_id_key
        """)
        print("   ✓ Unique constraint renamed")
    except psycopg2.errors.DuplicateTable:
        print("   ✓ Unique constraint already named correctly")
        conn.rollback()

    # Step 4: Update indexes
    print("\n4. Renaming indexes...")
    cursor.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'jobs'
        AND indexname LIKE 'idx_raw_jobs%'
    """)
    indexes = cursor.fetchall()
    for (idx_name,) in indexes:
        new_name = idx_name.replace('idx_raw_jobs', 'idx_jobs')
        cursor.execute(f'ALTER INDEX {idx_name} RENAME TO {new_name}')
        print(f"   ✓ {idx_name} → {new_name}")

    # Step 5: Clear user_job_matches (will be repopulated with new job IDs)
    print("\n5. Clearing user_job_matches...")
    cursor.execute("SELECT COUNT(*) FROM user_job_matches")
    old_count = cursor.fetchone()[0]
    cursor.execute("TRUNCATE TABLE user_job_matches RESTART IDENTITY")
    print(f"   ✓ Removed {old_count} old matches (will be regenerated)")

    # Step 6: Show new jobs table info
    print("\n6. New jobs table summary:")
    cursor.execute("SELECT COUNT(*) FROM jobs")
    job_count = cursor.fetchone()[0]
    print(f"   Total jobs: {job_count}")

    cursor.execute("""
        SELECT COUNT(*) FROM jobs
        WHERE ai_key_skills IS NOT NULL
        AND array_length(ai_key_skills, 1) > 0
    """)
    with_skills = cursor.fetchone()[0]
    print(f"   Jobs with AI skills: {with_skills} ({with_skills/job_count*100:.1f}%)")

    cursor.execute("""
        SELECT COUNT(*) FROM jobs
        WHERE ai_taxonomies_a IS NOT NULL
        AND array_length(ai_taxonomies_a, 1) > 0
    """)
    with_industries = cursor.fetchone()[0]
    print(f"   Jobs with industries: {with_industries} ({with_industries/job_count*100:.1f}%)")

    # Commit changes
    conn.commit()

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print("\nNew Architecture:")
    print("  ✓ jobs table = Pure global data (50+ AI metadata fields)")
    print("  ✓ user_job_matches table = User-specific matching data")
    print("  ✓ jobs_legacy_backup = Old table (for reference)")
    print("\nNext steps:")
    print("  1. Run hourly job collection to populate with fresh data")
    print("  2. Run matching for existing users")
    print("  3. Verify UI works with new structure")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Migrate to clean architecture')
    parser.add_argument('--confirm', action='store_true',
                        help='Confirm you want to proceed with migration')
    args = parser.parse_args()

    if not args.confirm:
        print("=" * 80)
        print("WARNING: This will:")
        print("  1. Backup current jobs table to jobs_legacy_backup")
        print("  2. Replace jobs table with raw_jobs_test (3,800 Germany jobs)")
        print("  3. Clear all user_job_matches (will be regenerated)")
        print("=" * 80)
        print("\nRun with --confirm flag to proceed:")
        print("  python scripts/migrate_to_clean_architecture.py --confirm")
        sys.exit(0)

    migrate()
