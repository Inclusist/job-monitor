#!/usr/bin/env python3
"""
Simple clean migration - start fresh with proper architecture
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

def migrate():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = False  # Use transactions
    cursor = conn.cursor()

    try:
        print("=" * 80)
        print("CLEAN MIGRATION - New Architecture")
        print("=" * 80)

        # Step 1: Drop old jobs table (backup first if needed)
        print("\n1. Removing old jobs table...")
        cursor.execute("DROP TABLE IF EXISTS jobs_legacy_backup CASCADE")
        cursor.execute("ALTER TABLE jobs RENAME TO jobs_legacy_backup")
        conn.commit()
        print("   ✓ Old jobs table backed up")

        # Step 2: Rename raw_jobs_test to jobs
        print("\n2. Creating new jobs table from raw_jobs_test...")
        cursor.execute("ALTER TABLE raw_jobs_test RENAME TO jobs")
        conn.commit()
        print("   ✓ raw_jobs_test → jobs")

        # Step 3: Rename sequence
        print("\n3. Updating sequences...")
        try:
            cursor.execute("ALTER SEQUENCE raw_jobs_test_id_seq RENAME TO jobs_id_seq")
            conn.commit()
            print("   ✓ Sequence renamed")
        except psycopg2.errors.DuplicateTable:
            # Sequence already exists, drop old and rename
            cursor.execute("DROP SEQUENCE IF EXISTS jobs_id_seq CASCADE")
            cursor.execute("ALTER SEQUENCE raw_jobs_test_id_seq RENAME TO jobs_id_seq")
            # Update the table to use the renamed sequence
            cursor.execute("ALTER TABLE jobs ALTER COLUMN id SET DEFAULT nextval('jobs_id_seq')")
            conn.commit()
            print("   ✓ Sequence renamed (replaced old)")

        # Step 4: Rename indexes
        print("\n4. Renaming indexes...")
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'jobs'
            AND indexname LIKE '%raw_jobs%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]

        for idx_name in indexes:
            new_name = idx_name.replace('raw_jobs_test', 'jobs').replace('raw_jobs', 'jobs')
            try:
                cursor.execute(f'ALTER INDEX {idx_name} RENAME TO {new_name}')
                print(f'   ✓ {idx_name} → {new_name}')
            except Exception as e:
                print(f'   ! Skipped {idx_name}: {e}')
                conn.rollback()

        conn.commit()

        # Step 5: Clear user_job_matches
        print("\n5. Clearing user_job_matches...")
        cursor.execute("SELECT COUNT(*) FROM user_job_matches")
        old_count = cursor.fetchone()[0]
        cursor.execute("TRUNCATE TABLE user_job_matches RESTART IDENTITY CASCADE")
        conn.commit()
        print(f"   ✓ Cleared {old_count} old matches")

        # Step 6: Summary
        print("\n6. New jobs table summary:")
        cursor.execute("SELECT COUNT(*) FROM jobs")
        job_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE ai_key_skills IS NOT NULL AND array_length(ai_key_skills, 1) > 0) as with_skills,
                COUNT(*) FILTER (WHERE ai_taxonomies_a IS NOT NULL AND array_length(ai_taxonomies_a, 1) > 0) as with_industries,
                MIN(posted_date) as min_date,
                MAX(posted_date) as max_date
            FROM jobs
        """)
        stats = cursor.fetchone()

        print(f"   Total jobs: {job_count:,}")
        print(f"   With AI skills: {stats[0]:,} ({stats[0]/job_count*100:.1f}%)")
        print(f"   With industries: {stats[1]:,} ({stats[1]/job_count*100:.1f}%)")
        print(f"   Date range: {stats[2]} to {stats[3]}")

        print("\n" + "=" * 80)
        print("MIGRATION SUCCESSFUL")
        print("=" * 80)
        print("\n✓ Clean architecture implemented:")
        print("  • jobs table = Global data (50+ AI fields)")
        print("  • user_job_matches table = User-specific data")
        print("  • jobs_legacy_backup = Old structure (backup)")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        raise

if __name__ == "__main__":
    migrate()
