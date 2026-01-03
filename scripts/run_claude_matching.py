#!/usr/bin/env python3
"""
Manually trigger Claude matching for jobs that only have semantic scores
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database
from src.matching.matcher import run_background_matching

load_dotenv()

def main():
    print("=" * 80)
    print("CLAUDE MATCHING - Manual Trigger")
    print("=" * 80)

    # Get user ID (you can pass as argument or prompt)
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    else:
        # Get first user from database
        db = get_database()
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users LIMIT 1")
        row = cursor.fetchone()
        cursor.close()

        if not row:
            print("❌ No users found in database")
            return

        user_id, email = row
        print(f"Using user: {email} (ID: {user_id})")

    # Run matching
    matching_status = {}
    print(f"\n🚀 Starting Claude matching for user {user_id}...")
    print("This will analyze jobs that only have semantic scores")
    print()

    run_background_matching(user_id, matching_status)

    # Print final status
    final_status = matching_status.get(user_id, {})
    print("\n" + "=" * 80)
    print("MATCHING COMPLETE")
    print("=" * 80)
    print(f"Status: {final_status.get('status')}")
    print(f"Jobs analyzed: {final_status.get('jobs_analyzed', 0)}")
    print(f"Matches found: {final_status.get('matches_found', 0)}")
    print(f"Message: {final_status.get('message', 'No message')}")
    print()

if __name__ == "__main__":
    main()
