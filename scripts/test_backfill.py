#!/usr/bin/env python3
"""
Test Backfill Script

Tests the backfill process using top 10 user search queries WITHOUT saving to database.
Useful for debugging and seeing how many jobs the backfill would find.

Usage:
    python scripts/test_backfill.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.jsearch import JSearchCollector
from src.collectors.activejobs_backfill import ActiveJobsBackfillCollector
from src.database.factory import get_database

load_dotenv()


def test_backfill():
    """Test backfill process without saving to database"""

    print("=" * 80)
    print("BACKFILL TEST (DRY RUN - NO DATABASE WRITES)")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get API keys
    jsearch_key = os.getenv('JSEARCH_API_KEY')
    activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')

    if not jsearch_key:
        print("⚠️  WARNING: JSEARCH_API_KEY not set - will skip JSearch")
    if not activejobs_key:
        print("⚠️  WARNING: ACTIVEJOBS_API_KEY not set - will skip Active Jobs DB")

    if not jsearch_key and not activejobs_key:
        print("❌ ERROR: No API keys configured!")
        return False

    # Initialize database
    db = get_database()

    try:
        # Get top 10 user search queries
        print("📊 Fetching top 10 user search queries...\n")
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                title_keyword,
                location,
                ai_work_arrangement,
                ai_employment_type,
                ai_seniority,
                ai_industry,
                priority
            FROM user_search_queries
            WHERE is_active = TRUE
            ORDER BY priority DESC, id ASC
            LIMIT 10
        """)

        queries = []
        for row in cursor.fetchall():
            queries.append({
                'title_keyword': row[0],
                'location': row[1],
                'ai_work_arrangement': row[2],
                'ai_employment_type': row[3],
                'ai_seniority': row[4],
                'ai_industry': row[5],
                'priority': row[6]
            })

        cursor.close()
        db._return_connection(conn)

        if not queries:
            print("⚠️  No search queries found in database!")
            print("Using sample queries for testing...\n")

            # Use sample queries for testing
            queries = [
                {'title_keyword': 'Data Science Manager', 'location': 'Berlin, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'high'},
                {'title_keyword': 'Data Science Manager', 'location': 'Hamburg, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'high'},
                {'title_keyword': 'Head of Data Science', 'location': 'Berlin, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'high'},
                {'title_keyword': 'Head of Data Science', 'location': 'Hamburg, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'high'},
                {'title_keyword': 'Team Lead Data Science', 'location': 'Berlin, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'medium'},
                {'title_keyword': 'Team Lead Data Science', 'location': 'Hamburg, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'medium'},
                {'title_keyword': 'Team Lead Machine Learning', 'location': 'Berlin, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'medium'},
                {'title_keyword': 'Team Lead Data', 'location': 'Berlin, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'medium'},
                {'title_keyword': 'Senior Data Scientist', 'location': 'Berlin, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'low'},
                {'title_keyword': 'Machine Learning Engineer', 'location': 'Berlin, Germany', 'ai_work_arrangement': None, 'ai_employment_type': None, 'ai_seniority': None, 'ai_industry': None, 'priority': 'low'},
            ]

        print(f"Found {len(queries)} search queries:")
        for i, q in enumerate(queries, 1):
            print(f"  {i}. {q['title_keyword']} in {q['location']}")
        print()

        # Collect all jobs (without saving)
        all_jobs = []
        stats = {
            'jsearch_jobs': 0,
            'activejobs_jobs': 0,
            'total_jobs': 0
        }

        # Test JSearch
        if jsearch_key:
            print("=" * 80)
            print("TESTING JSEARCH (1-month backfill)")
            print("=" * 80)

            jsearch_collector = JSearchCollector(jsearch_key, enable_filtering=True, min_quality=2)

            # Get unique title+location combinations
            combinations = set()
            for query in queries:
                title = query.get('title_keyword')
                location = query.get('location')

                if not title:
                    continue

                is_remote = location and location.lower() == 'remote'

                if is_remote:
                    combinations.add((title, None, True))
                else:
                    combinations.add((title, location, False))

            print(f"\nSearching {len(combinations)} title+location combinations...\n")

            for title, location, is_remote in combinations:
                display = f"{title} (remote only)" if is_remote else f"{title} in {location}" if location else title
                print(f"  Searching: {display}")

                jobs = jsearch_collector.search_jobs(
                    query=title,
                    location=location,
                    num_pages=10,
                    date_posted="month",
                    country="de",
                    remote_jobs_only=is_remote
                )

                all_jobs.extend(jobs)
                stats['jsearch_jobs'] += len(jobs)
                print(f"    ✓ Found {len(jobs)} jobs")

            print(f"\n📊 JSearch Total: {stats['jsearch_jobs']} jobs\n")

        # Test Active Jobs DB
        if activejobs_key:
            print("=" * 80)
            print("TESTING ACTIVE JOBS DB (6-month backfill)")
            print("=" * 80)

            activejobs_collector = ActiveJobsBackfillCollector(activejobs_key)

            # Collect all unique titles and locations
            all_titles = set()
            specific_locations = set()

            for query in queries:
                title = query.get('title_keyword')
                if title:
                    all_titles.add(title)

                location = query.get('location', 'Germany')
                if location and location not in ['Germany', 'Remote'] and location.lower() != 'remote':
                    specific_locations.add(location)

            # Format titles for advanced_title_filter: 'title1' | 'title2' | 'title3'
            piped_titles = ' | '.join(f"'{title}'" for title in sorted(all_titles)) if all_titles else None

            if piped_titles:
                print(f"\nTitles: {piped_titles}")
                print(f"Specific locations: {', '.join(sorted(specific_locations)) if specific_locations else 'None'}\n")

                # STRATEGY 1: City-specific searches
                if specific_locations:
                    print(f"📍 STRATEGY 1: Searching {len(specific_locations)} specific locations for ALL jobs...\n")

                    for location in sorted(specific_locations):
                        # Clean location - remove ", Germany" suffix if present
                        clean_location = location.split(',')[0].strip() if ',' in location else location
                        print(f"  Location: {location} (searching as: {clean_location})")

                        jobs = activejobs_collector.search_backfill(
                            query=piped_titles,
                            location=clean_location,
                            limit=500
                        )

                        all_jobs.extend(jobs)
                        stats['activejobs_jobs'] += len(jobs)
                        print(f"    ✓ Found {len(jobs)} jobs\n")

                # STRATEGY 2: Germany-wide remote/hybrid
                print("🌍 STRATEGY 2: Searching Germany for remote/hybrid jobs...\n")
                print(f"  Location: Germany")
                print(f"  Work arrangements: Hybrid,Remote OK,Remote Solely")

                jobs = activejobs_collector.search_backfill(
                    query=piped_titles,
                    location="Germany",
                    limit=500,
                    ai_work_arrangement="Hybrid,Remote OK,Remote Solely"
                )

                all_jobs.extend(jobs)
                stats['activejobs_jobs'] += len(jobs)
                print(f"    ✓ Found {len(jobs)} jobs\n")

            print(f"📊 Active Jobs DB Total: {stats['activejobs_jobs']} jobs\n")

        # Final statistics
        stats['total_jobs'] = len(all_jobs)

        print("=" * 80)
        print("BACKFILL TEST RESULTS")
        print("=" * 80)
        print(f"\nJobs Found:")
        print(f"  JSearch: {stats['jsearch_jobs']}")
        print(f"  Active Jobs DB: {stats['activejobs_jobs']}")
        print(f"  Total (before deduplication): {stats['total_jobs']}")

        # Check for duplicates
        seen_ids = set()
        duplicates = 0
        for job in all_jobs:
            job_id = job.get('external_id') or job.get('job_id') or job.get('url', '')
            if job_id in seen_ids:
                duplicates += 1
            else:
                seen_ids.add(job_id)

        unique_jobs = stats['total_jobs'] - duplicates
        print(f"\nDeduplication:")
        print(f"  Duplicates: {duplicates}")
        print(f"  Unique jobs: {unique_jobs}")

        if unique_jobs > 0:
            print(f"\n✅ SUCCESS! Found {unique_jobs} unique jobs")
            print(f"\nSample jobs:")
            for i, job in enumerate(all_jobs[:5], 1):
                print(f"  {i}. {job.get('title')} at {job.get('company')} - {job.get('location')}")
        else:
            print(f"\n⚠️  No jobs found - check API keys and query settings")

        print("\n" + "=" * 80)
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ ERROR during test: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = test_backfill()
    sys.exit(0 if success else 1)
