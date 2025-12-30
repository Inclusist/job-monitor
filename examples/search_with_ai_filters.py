#!/usr/bin/env python3
"""
Example: Using AI field filters for advanced job searching

Demonstrates the new search_jobs_with_filters and search_jobs_with_or_filters methods
that support filtering by AI-extracted metadata like work arrangement, seniority, etc.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database

load_dotenv()


def example_simple_filters():
    """Example 1: Simple filtering by AI fields"""
    print("=" * 60)
    print("Example 1: Simple Filtering by AI Fields")
    print("=" * 60)

    db = get_database()

    # Find all remote jobs
    print("\n1. Finding remote jobs...")
    remote_jobs = db.search_jobs_with_filters(
        work_arrangement='remote',
        limit=10
    )
    print(f"Found {len(remote_jobs)} remote jobs")
    for job in remote_jobs[:3]:
        print(f"  - {job['title']} at {job['company']} ({job['ai_work_arrangement']})")

    # Find senior-level positions
    print("\n2. Finding senior-level positions...")
    senior_jobs = db.search_jobs_with_filters(
        seniority='senior',
        min_score=70,
        limit=10
    )
    print(f"Found {len(senior_jobs)} senior positions with score >= 70")
    for job in senior_jobs[:3]:
        print(f"  - {job['title']} at {job['company']} (Score: {job['match_score']}, Seniority: {job['ai_seniority']})")

    # Find full-time jobs in technology industry
    print("\n3. Finding full-time technology jobs...")
    tech_jobs = db.search_jobs_with_filters(
        employment_type='full-time',
        industry='technology',
        limit=10
    )
    print(f"Found {len(tech_jobs)} full-time technology jobs")
    for job in tech_jobs[:3]:
        print(f"  - {job['title']} at {job['company']} ({job['ai_employment_type']}, {job['ai_industry']})")


def example_complex_query():
    """Example 2: Complex query - Berlin OR (Hybrid AND NOT Berlin)"""
    print("\n" + "=" * 60)
    print("Example 2: Complex Query - Berlin OR (Hybrid NOT in Berlin)")
    print("=" * 60)

    db = get_database()

    # Method 1: Using search_jobs_with_or_filters
    print("\nMethod 1: Using search_jobs_with_or_filters()...")
    filter_groups = [
        {'location': 'Berlin'},  # Jobs in Berlin
        {'work_arrangement': 'Hybrid', 'location': 'Berlin', 'exclude_location': True}  # Hybrid jobs NOT in Berlin
    ]

    jobs = db.search_jobs_with_or_filters(filter_groups, limit=20)
    print(f"Found {len(jobs)} jobs matching criteria")

    berlin_count = sum(1 for job in jobs if 'Berlin' in job.get('location', ''))
    hybrid_non_berlin = sum(1 for job in jobs if 'Hybrid' in job.get('ai_work_arrangement', '') and 'Berlin' not in job.get('location', ''))

    print(f"  - {berlin_count} jobs in Berlin")
    print(f"  - {hybrid_non_berlin} hybrid jobs not in Berlin")

    print("\nSample results:")
    for job in jobs[:5]:
        print(f"  - {job['title']} at {job['company']}")
        print(f"    Location: {job['location']}, Work: {job['ai_work_arrangement']}")

    # Method 2: Manual combination (more control)
    print("\nMethod 2: Manual combination of results...")
    berlin_jobs = db.search_jobs_with_filters(location='Berlin', limit=20)
    hybrid_not_berlin = db.search_jobs_with_filters(
        work_arrangement='Hybrid',
        location='Berlin',
        exclude_location=True,
        limit=20
    )

    # Combine and deduplicate
    combined_jobs = berlin_jobs.copy()
    seen_ids = {job['id'] for job in berlin_jobs}

    for job in hybrid_not_berlin:
        if job['id'] not in seen_ids:
            combined_jobs.append(job)
            seen_ids.add(job['id'])

    print(f"Found {len(combined_jobs)} total jobs")
    print(f"  - {len(berlin_jobs)} in Berlin")
    print(f"  - {len(hybrid_not_berlin)} hybrid jobs not in Berlin")


def example_combined_filters():
    """Example 3: Combining multiple AI field filters"""
    print("\n" + "=" * 60)
    print("Example 3: Combining Multiple Filters")
    print("=" * 60)

    db = get_database()

    # Remote senior positions in technology
    print("\nFinding remote senior technology positions...")
    jobs = db.search_jobs_with_filters(
        work_arrangement='remote',
        seniority='senior',
        industry='technology',
        min_score=75,
        limit=15
    )

    print(f"Found {len(jobs)} matching jobs")
    for job in jobs[:5]:
        print(f"  - {job['title']} at {job['company']}")
        print(f"    Score: {job['match_score']}, {job['ai_work_arrangement']}, {job['ai_seniority']}, {job['ai_industry']}")


def example_location_and_work_arrangement():
    """Example 4: Location + Work Arrangement combinations"""
    print("\n" + "=" * 60)
    print("Example 4: Location + Work Arrangement Combinations")
    print("=" * 60)

    db = get_database()

    # Scenario: User wants Munich onsite OR anywhere remote
    print("\nScenario: Munich onsite OR anywhere remote...")
    filter_groups = [
        {'location': 'Munich', 'work_arrangement': 'onsite'},
        {'work_arrangement': 'remote'}
    ]

    jobs = db.search_jobs_with_or_filters(filter_groups, limit=20)
    print(f"Found {len(jobs)} jobs")

    munich_onsite = sum(1 for job in jobs if 'Munich' in job.get('location', '') and 'onsite' in job.get('ai_work_arrangement', '').lower())
    remote_any = sum(1 for job in jobs if 'remote' in job.get('ai_work_arrangement', '').lower())

    print(f"  - {munich_onsite} onsite jobs in Munich")
    print(f"  - {remote_any} remote jobs anywhere")


def main():
    """Run all examples"""
    try:
        example_simple_filters()
        example_complex_query()
        example_combined_filters()
        example_location_and_work_arrangement()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
