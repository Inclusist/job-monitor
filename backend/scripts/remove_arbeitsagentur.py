#!/usr/bin/env python3
"""
Remove Arbeitsagentur jobs from database
These jobs have no descriptions and are unusable for matching
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def remove_arbeitsagentur_jobs():
    """Remove all Arbeitsagentur jobs from database"""
    print_header("REMOVING ARBEITSAGENTUR JOBS")

    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    # First, check what we're about to delete
    print("\n📊 Checking Arbeitsagentur jobs...")
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM jobs
        WHERE source = 'Arbeitsagentur'
    """)

    count = cursor.fetchone()[0]
    print(f"  Found {count} Arbeitsagentur jobs")

    if count == 0:
        print("\n✅ No Arbeitsagentur jobs to remove")
        db._return_connection(conn)
        return

    # Show some examples
    print("\n📋 Sample jobs to be deleted:")
    cursor.execute("""
        SELECT title, company, location, LENGTH(description) as desc_len
        FROM jobs
        WHERE source = 'Arbeitsagentur'
        LIMIT 5
    """)

    for row in cursor.fetchall():
        title, company, location, desc_len = row
        print(f"  • {title} at {company} ({location}) - {desc_len} chars")

    # Get confirmation (though user already approved)
    print(f"\n⚠️  About to delete {count} Arbeitsagentur jobs...")
    print("   Reason: No job descriptions available (avg 76 chars)")
    print("   Impact: Cannot be used for semantic matching or Claude analysis")

    # Delete the jobs
    print("\n🗑️  Deleting jobs...")
    cursor.execute("""
        DELETE FROM jobs
        WHERE source = 'Arbeitsagentur'
    """)

    deleted_count = cursor.rowcount
    conn.commit()

    print(f"✅ Deleted {deleted_count} jobs")

    # Show updated database stats
    print("\n📊 Updated database status:")
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM jobs
        GROUP BY source
        ORDER BY count DESC
    """)

    total = 0
    for row in cursor.fetchall():
        source, count = row
        total += count
        print(f"  {source}: {count} jobs")

    print(f"\n  Total jobs remaining: {total}")

    # Calculate quality improvement
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM jobs
        WHERE LENGTH(description) > 200
    """)

    quality_count = cursor.fetchone()[0]
    quality_rate = (quality_count / total * 100) if total > 0 else 0

    print(f"\n📈 Quality improvement:")
    print(f"  Jobs with good descriptions (>200 chars): {quality_count}/{total} ({quality_rate:.1f}%)")

    db._return_connection(conn)

    print("\n✅ Cleanup complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    remove_arbeitsagentur_jobs()
