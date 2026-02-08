#!/usr/bin/env python3
"""
Example: Using API-level AI filters with Active Jobs DB

Demonstrates how to filter jobs at the API level using AI-extracted metadata,
which is much more efficient than fetching all jobs and filtering locally.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.activejobs import ActiveJobsCollector

load_dotenv()


def example_api_level_filters():
    """
    Example: Using API-level filters to fetch only relevant jobs

    This reduces quota consumption since you only fetch jobs that match your criteria
    """
    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    if not api_key:
        print("Error: ACTIVEJOBS_API_KEY not set")
        return

    collector = ActiveJobsCollector(api_key)

    print("=" * 60)
    print("API-Level Filtering Examples")
    print("=" * 60)

    # Example 1: Search for remote senior positions in Germany
    print("\n1. Remote Senior Positions in Germany")
    print("-" * 60)
    jobs = collector.search_jobs(
        query="software engineer",
        location="Germany",
        ai_work_arrangement="remote",
        ai_seniority="senior",
        num_pages=1,
        results_per_page=10
    )
    print(f"Found {len(jobs)} remote senior software engineer jobs")
    for job in jobs[:3]:
        print(f"  - {job['title']} at {job['company']}")
        print(f"    Location: {job['location']}")
        print(f"    Work: {job['ai_work_arrangement']}, Seniority: {job['ai_seniority']}")

    # Example 2: Hybrid jobs in technology industry
    print("\n2. Hybrid Technology Jobs")
    print("-" * 60)
    jobs = collector.search_jobs(
        query="developer",
        location="Germany",
        ai_work_arrangement="hybrid",
        ai_industry="technology",
        num_pages=1,
        results_per_page=10
    )
    print(f"Found {len(jobs)} hybrid technology developer jobs")
    for job in jobs[:3]:
        print(f"  - {job['title']} at {job['company']}")
        print(f"    Work: {job['ai_work_arrangement']}, Industry: {job['ai_industry']}")

    # Example 3: Full-time entry-level positions
    print("\n3. Full-time Entry-level Positions")
    print("-" * 60)
    jobs = collector.search_jobs(
        query="junior developer",
        location="Berlin",
        ai_employment_type="full-time",
        ai_seniority="entry",
        num_pages=1,
        results_per_page=10
    )
    print(f"Found {len(jobs)} full-time entry-level jobs in Berlin")
    for job in jobs[:3]:
        print(f"  - {job['title']} at {job['company']}")
        print(f"    Type: {job['ai_employment_type']}, Seniority: {job['ai_seniority']}")


def example_bulk_fetch_with_filters():
    """
    Example: Bulk fetching with API filters

    Useful for building initial database while respecting quota limits
    """
    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    if not api_key:
        print("Error: ACTIVEJOBS_API_KEY not set")
        return

    collector = ActiveJobsCollector(api_key)

    print("\n" + "=" * 60)
    print("Bulk Fetch with AI Filters")
    print("=" * 60)

    # Example: Fetch all remote jobs in Germany from last 24h
    print("\nFetching remote jobs in Germany (last 24h)...")
    jobs = collector.search_all_recent_jobs(
        location="Germany",
        max_pages=2,  # 200 jobs max
        date_posted="24h",
        ai_work_arrangement="remote"
    )

    print(f"\nFetched {len(jobs)} remote jobs")
    print(f"This uses approximately {len(jobs)} of your monthly quota")

    # Show breakdown
    by_seniority = {}
    by_industry = {}

    for job in jobs:
        seniority = job.get('ai_seniority', 'Not specified')
        industry = job.get('ai_industry', 'Not specified')

        by_seniority[seniority] = by_seniority.get(seniority, 0) + 1
        by_industry[industry] = by_industry.get(industry, 0) + 1

    print("\nBreakdown by Seniority:")
    for level, count in sorted(by_seniority.items(), key=lambda x: x[1], reverse=True):
        print(f"  {level}: {count}")

    print("\nBreakdown by Industry:")
    for ind, count in sorted(by_industry.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {ind}: {count}")


def example_quota_efficient_search():
    """
    Example: Quota-efficient search strategy

    Use API filters to minimize quota usage
    """
    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    if not api_key:
        print("Error: ACTIVEJOBS_API_KEY not set")
        return

    collector = ActiveJobsCollector(api_key)

    print("\n" + "=" * 60)
    print("Quota-Efficient Search Strategy")
    print("=" * 60)

    # Strategy: Instead of fetching all jobs and filtering locally,
    # use multiple targeted API calls with specific filters

    search_configs = [
        {
            'name': 'Remote Senior Tech',
            'filters': {
                'query': 'engineer',
                'location': 'Germany',
                'ai_work_arrangement': 'remote',
                'ai_seniority': 'senior',
                'ai_industry': 'technology'
            }
        },
        {
            'name': 'Hybrid Mid-level',
            'filters': {
                'query': 'developer',
                'location': 'Berlin',
                'ai_work_arrangement': 'hybrid',
                'ai_seniority': 'mid'
            }
        }
    ]

    total_jobs = 0

    for config in search_configs:
        print(f"\nSearching: {config['name']}")
        jobs = collector.search_jobs(
            **config['filters'],
            num_pages=1,
            results_per_page=20
        )
        print(f"  Found {len(jobs)} jobs")
        total_jobs += len(jobs)

    print(f"\nTotal jobs fetched: {total_jobs}")
    print(f"Quota used: ~{total_jobs} jobs (vs fetching all and filtering locally)")


if __name__ == "__main__":
    try:
        example_api_level_filters()
        example_bulk_fetch_with_filters()
        example_quota_efficient_search()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
