#!/usr/bin/env python3
"""
Re-run job matching with enhanced Claude analysis

This script:
1. Clears old matches (from before Claude enhancement)
2. Runs new matching with 50% threshold + enhanced Claude prompt
3. Shows statistics

Usage:
    python scripts/rerun_matching_with_enhanced_claude.py
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.matching.matcher import run_background_matching
from src.database.factory import get_database
import psycopg2


def main():
    print("=" * 60)
    print("RE-RUN MATCHING WITH ENHANCED CLAUDE")
    print("=" * 60)

    # Get database
    db = get_database()

    # Get user
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email FROM users LIMIT 1")
    row = cursor.fetchone()

    if not row:
        print("❌ No users found")
        cursor.close()
        db._return_connection(conn)
        return

    user_id, user_email = row[0], row[1]

    print(f"\nUser: {user_email}")
    print(f"User ID: {user_id}")

    # Check current matches
    cursor.execute("SELECT COUNT(*) FROM user_job_matches WHERE user_id = %s", (user_id,))
    old_matches = cursor.fetchone()[0]
    print(f"\nCurrent matches: {old_matches:,}")

    # Clear old matches
    print("\n🗑️  Clearing old matches...")
    cursor.execute("DELETE FROM user_job_matches WHERE user_id = %s", (user_id,))
    conn.commit()
    print(f"   ✓ Cleared {old_matches:,} old matches")

    cursor.close()
    db._return_connection(conn)

    # Check total jobs available
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]
    cursor.close()
    db._return_connection(conn)

    print(f"\n📊 Total jobs to match against: {total_jobs:,}")
    print(f"\n🚀 Starting enhanced matching...")
    print(f"   • Semantic threshold: ≥30%")
    print(f"   • Claude threshold: ≥50% (NEW - was 70%)")
    print(f"   • Enhanced Claude prompt with AI metadata")
    print()

    # Run matching
    matching_status = {}

    try:
        run_background_matching(user_id, matching_status)

        # Print results
        final_status = matching_status.get(user_id, {})

        print("\n" + "=" * 60)

        if final_status.get('status') == 'completed':
            print("✅ MATCHING COMPLETE!")
            print("=" * 60)
            print(f"Matches found: {final_status.get('matches_found', 0):,}")
            print(f"Jobs analyzed by Claude: {final_status.get('jobs_analyzed', 0):,}")

            # Show breakdown
            conn = db._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE claude_score IS NOT NULL) as with_claude,
                    COUNT(*) FILTER (WHERE claude_score IS NULL) as without_claude
                FROM user_job_matches
                WHERE user_id = %s
            """, (user_id,))
            row = cursor.fetchone()

            print(f"\nWith Claude analysis: {row[0]:,}")
            print(f"Semantic only: {row[1]:,}")

            if row[0] > 0:
                cursor.execute("""
                    SELECT j.source, COUNT(*) as count
                    FROM user_job_matches ujm
                    JOIN jobs j ON ujm.job_id = j.id
                    WHERE ujm.user_id = %s AND ujm.claude_score IS NOT NULL
                    GROUP BY j.source
                    ORDER BY count DESC
                    LIMIT 10
                """, (user_id,))

                print("\nTop sources with Claude analysis:")
                for row in cursor.fetchall():
                    print(f"  {row[0]}: {row[1]:,}")

            cursor.close()
            db._return_connection(conn)

            print(f"\n💡 View jobs at http://localhost:5000/jobs")
        else:
            print(f"⚠️ Matching status: {final_status.get('status')}")
            print(f"Message: {final_status.get('message')}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
