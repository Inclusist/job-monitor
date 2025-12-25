#!/usr/bin/env python3
"""
One-time bulk loader for Arbeitsagentur jobs

Aggregates all keyword+location combinations from all users and loads
jobs from the last 30 days for each combination.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.factory import create_database_manager, create_cv_manager
from src.collectors.arbeitsagentur import ArbeitsagenturCollector
from datetime import datetime
import time
from collections import defaultdict
import yaml

def load_config():
    """Load config.yaml for default keywords/locations"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_all_user_combinations(cv_manager):
    """
    Aggregate all unique keyword+location combinations from all users

    Returns:
        dict: {(keyword, location): [user_ids]} mapping
    """
    print("\n" + "="*80)
    print("AGGREGATING SEARCH COMBINATIONS FROM ALL USERS")
    print("="*80)

    # Get all users - need to query database directly
    conn = cv_manager._get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, email, preferences FROM users WHERE is_active = 1")
        users = cursor.fetchall()
    except:
        # PostgreSQL
        cursor.execute("SELECT id, email, preferences FROM users WHERE is_active = true")
        users = cursor.fetchall()

    cursor.close()
    cv_manager._return_connection(conn)

    # Load default config
    config = load_config()
    default_keywords = config.get('search_config', {}).get('keywords', [])
    default_locations = config.get('search_config', {}).get('locations', [])

    print(f"\n📊 Found {len(users)} active users")
    print(f"📋 Default config: {len(default_keywords)} keywords, {len(default_locations)} locations")

    # Aggregate combinations
    combinations = defaultdict(list)

    for user in users:
        user_id = user[0]
        user_email = user[1]
        preferences = user[2]

        # Parse preferences
        if preferences:
            if isinstance(preferences, str):
                import json
                try:
                    preferences = json.loads(preferences)
                except:
                    preferences = {}

            keywords = preferences.get('search_keywords', [])
            locations = preferences.get('search_locations', [])
        else:
            keywords = []
            locations = []

        # Fall back to defaults if user has no preferences
        if not keywords:
            keywords = default_keywords
        if not locations:
            locations = default_locations

        print(f"\n👤 User {user_id} ({user_email})")
        print(f"   Keywords: {', '.join(keywords[:5])}{' ...' if len(keywords) > 5 else ''}")
        print(f"   Locations: {', '.join(locations)}")

        # Add all combinations for this user
        for keyword in keywords:
            for location in locations:
                combinations[(keyword, location)].append(user_id)

    print(f"\n✅ Total unique combinations: {len(combinations)}")
    print("\n" + "="*80)

    return combinations

def bulk_load_jobs(combinations, job_db):
    """
    Load jobs from Arbeitsagentur for all combinations

    Args:
        combinations: dict of {(keyword, location): [user_ids]}
        job_db: Database manager instance
    """
    print("\n" + "="*80)
    print("BULK LOADING JOBS FROM ARBEITSAGENTUR")
    print("="*80)

    collector = ArbeitsagenturCollector()

    total_jobs_fetched = 0
    total_jobs_stored = 0
    failed_searches = []

    print(f"\n🔍 Processing {len(combinations)} unique keyword+location combinations")
    print(f"📅 Fetching jobs from last 30 days")
    print(f"⏱️  Estimated time: {len(combinations) * 2} seconds (~2s per search)")
    print()

    start_time = time.time()

    for idx, ((keyword, location), user_ids) in enumerate(combinations.items(), 1):
        print(f"\n[{idx}/{len(combinations)}] {keyword} in {location}")
        print(f"   Used by {len(user_ids)} user(s): {user_ids}")

        try:
            # Search Arbeitsagentur for this combination
            # Use 30 days since posted (but API might round to nearest safe value)
            result = collector.search_jobs(
                keywords=keyword,
                location=location,
                days_since_posted=30,  # Last 30 days
                page_size=100,  # Max results per page
                page=1
            )

            if not result.get('success'):
                print(f"   ❌ Search failed: {result.get('message', 'Unknown error')}")
                failed_searches.append((keyword, location, result.get('message')))
                continue

            jobs = result.get('stellenangebote', [])
            total_results = result.get('maxErgebnisse', 0)

            print(f"   📊 Found {total_results} total results, fetched {len(jobs)}")

            # Parse and store jobs
            stored_count = 0
            for job_data in jobs:
                try:
                    parsed_job = collector.parse_job(job_data)
                    if parsed_job:
                        job_db.add_job(parsed_job)
                        stored_count += 1
                except Exception as e:
                    print(f"      ⚠️  Error storing job: {e}")
                    continue

            total_jobs_fetched += len(jobs)
            total_jobs_stored += stored_count

            print(f"   ✅ Stored {stored_count}/{len(jobs)} jobs")

            # Rate limiting - be nice to the API
            time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed_searches.append((keyword, location, str(e)))
            continue

    elapsed_time = time.time() - start_time

    print("\n" + "="*80)
    print("BULK LOAD SUMMARY")
    print("="*80)
    print(f"\n📊 Statistics:")
    print(f"   Combinations processed: {len(combinations)}")
    print(f"   Jobs fetched: {total_jobs_fetched}")
    print(f"   Jobs stored: {total_jobs_stored}")
    print(f"   Failed searches: {len(failed_searches)}")
    print(f"   Time elapsed: {elapsed_time:.1f} seconds")
    print(f"   Average per search: {elapsed_time/len(combinations):.2f}s")

    if failed_searches:
        print(f"\n❌ Failed Searches ({len(failed_searches)}):")
        for keyword, location, error in failed_searches[:10]:
            print(f"   - {keyword} in {location}: {error}")
        if len(failed_searches) > 10:
            print(f"   ... and {len(failed_searches) - 10} more")

    print("\n✅ Bulk load complete!")
    print("="*80 + "\n")

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("ARBEITSAGENTUR BULK LOADER")
    print("="*80)
    print("\nThis script will:")
    print("1. Aggregate all keyword+location combinations from all users")
    print("2. Fetch jobs from Arbeitsagentur for each combination (last 30 days)")
    print("3. Store all jobs in the database")
    print("\nThis is a ONE-TIME operation to populate your job database.")
    print("="*80)

    # Confirm
    confirm = input("\n⚠️  Proceed with bulk load? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n❌ Bulk load cancelled.")
        return

    # Initialize database
    print("\n🔧 Initializing database...")
    job_db = create_database_manager()
    cv_manager = create_cv_manager(job_db)

    # Get all combinations
    combinations = get_all_user_combinations(cv_manager)

    if not combinations:
        print("\n❌ No user combinations found. Make sure users have search preferences set.")
        return

    # Show summary and confirm again
    print(f"\n📊 Ready to fetch jobs for {len(combinations)} combinations")
    confirm2 = input("⚠️  This may take several minutes. Continue? (yes/no): ").strip().lower()
    if confirm2 != 'yes':
        print("\n❌ Bulk load cancelled.")
        return

    # Bulk load
    bulk_load_jobs(combinations, job_db)

    print("\n🎉 All done! Check your database for new jobs.")

if __name__ == '__main__':
    main()
