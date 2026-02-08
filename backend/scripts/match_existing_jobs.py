#!/usr/bin/env python3
"""
Match existing jobs in database against user's CV
Runs semantic matching + enhanced Claude analysis

Usage:
    python scripts/match_existing_jobs.py
    python scripts/match_existing_jobs.py --email user@example.com
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.matching.matcher import run_background_matching
from src.database.factory import get_database
import argparse


def main():
    parser = argparse.ArgumentParser(description='Match existing jobs against user CV')
    parser.add_argument(
        '--email',
        type=str,
        help='User email (if not provided, uses first user in database)'
    )
    args = parser.parse_args()

    # Get database
    db = get_database()

    # Get user
    if args.email:
        user = db.get_user_by_email(args.email)
        if not user:
            print(f"❌ User not found: {args.email}")
            sys.exit(1)
    else:
        # Get first user
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        db._return_connection(conn)

        if not row:
            print("❌ No users found in database")
            print("💡 Upload a CV first via the web UI")
            sys.exit(1)

        user = {'id': row[0], 'email': row[1]}

    print(f"\n{'='*60}")
    print(f"MATCHING EXISTING JOBS")
    print(f"{'='*60}")
    print(f"User: {user['email']}")
    print(f"User ID: {user['id']}")
    print(f"{'='*60}\n")

    # Check job count
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]
    cursor.close()
    db._return_connection(conn)

    print(f"📊 Total jobs in database: {total_jobs:,}")
    print(f"🔄 Starting full matching pipeline...\n")
    print(f"   Step 1: Semantic matching (sentence transformers)")
    print(f"   Step 2: Enhanced Claude analysis (≥50% matches)\n")

    # Run matching
    matching_status = {}

    try:
        run_background_matching(user['id'], matching_status)

        # Print final status
        final_status = matching_status.get(user['id'], {})

        if final_status.get('status') == 'completed':
            print(f"\n{'='*60}")
            print("✅ MATCHING COMPLETE")
            print(f"{'='*60}")
            print(f"Matches found: {final_status.get('matches_found', 0)}")
            print(f"Jobs analyzed by Claude: {final_status.get('jobs_analyzed', 0)}")
            print(f"\n💡 View your matched jobs in the web UI at /jobs")
        else:
            print(f"\n⚠️ Matching finished with status: {final_status.get('status')}")
            print(f"Message: {final_status.get('message')}")

    except Exception as e:
        print(f"\n❌ Error during matching: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    db.close()


if __name__ == "__main__":
    main()
