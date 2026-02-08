#!/usr/bin/env python3
"""
Reset User Queries and Backfill Tracking

Clears user_search_queries and backfill_tracking tables to test fresh backfill.
Useful for debugging and testing the backfill process.

CAUTION: This will delete all user queries and backfill history!
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database

load_dotenv()


def reset_tables(user_email: str = None):
    """
    Reset user query and backfill tracking tables

    Args:
        user_email: Optional - reset only for specific user, otherwise reset all
    """
    db = get_database()

    try:
        conn = db._get_connection()
        cursor = conn.cursor()

        if user_email:
            # Reset for specific user
            print(f"\n🔄 Resetting queries and backfill tracking for user: {user_email}")

            # Get user ID
            cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
            user_row = cursor.fetchone()

            if not user_row:
                print(f"❌ User not found: {user_email}")
                return False

            user_id = user_row[0]

            # Delete user's search queries
            cursor.execute("DELETE FROM user_search_queries WHERE user_id = %s", (user_id,))
            queries_deleted = cursor.rowcount
            print(f"✓ Deleted {queries_deleted} search queries for user")

            # Get user's query combinations for backfill tracking cleanup
            # Since we deleted the queries, we need to delete all backfill tracking
            # (we can't know which combinations belonged to this user)
            # For safety, we'll just delete all backfill tracking when resetting a user
            cursor.execute("DELETE FROM backfill_tracking")
            backfill_deleted = cursor.rowcount
            print(f"✓ Deleted {backfill_deleted} backfill tracking records (all)")

        else:
            # Reset everything
            print("\n🔄 Resetting ALL queries and backfill tracking...")
            print("⚠️  WARNING: This will delete all user queries and backfill history!")

            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cancelled")
                return False

            cursor.execute("DELETE FROM user_search_queries")
            queries_deleted = cursor.rowcount
            print(f"✓ Deleted {queries_deleted} search queries")

            cursor.execute("DELETE FROM backfill_tracking")
            backfill_deleted = cursor.rowcount
            print(f"✓ Deleted {backfill_deleted} backfill tracking records")

        conn.commit()
        print("\n✅ Reset completed successfully!")
        print("\nYou can now:")
        print("  1. Re-upload CV to trigger fresh backfill")
        print("  2. Watch the backfill output to see how many jobs are found")
        print("  3. Check for any filtering or deduplication issues")

        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error resetting tables: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        db._return_connection(conn)
        db.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Reset user queries and backfill tracking')
    parser.add_argument(
        '--user',
        type=str,
        help='Email of specific user to reset (if not provided, resets ALL users)'
    )
    args = parser.parse_args()

    print("=" * 70)
    print("RESET USER QUERIES & BACKFILL TRACKING")
    print("=" * 70)

    if args.user:
        success = reset_tables(user_email=args.user)
    else:
        success = reset_tables()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
