#!/usr/bin/env python3
"""
Debug Active Jobs DB results to see what we're actually getting
"""

import os
import sys
from dotenv import load_dotenv
from collections import Counter

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.activejobs import ActiveJobsCollector


def main():
    print("=" * 60)
    print("DEBUGGING ACTIVE JOBS DB RESULTS")
    print("=" * 60)

    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    collector = ActiveJobsCollector(api_key)

    print("\n🔍 Fetching recent jobs from Germany...")
    jobs = collector.search_all_recent_jobs(
        location="Germany",
        max_pages=2,  # Just 2 pages for debugging
        date_posted="week"
    )

    print(f"\n✅ Fetched {len(jobs)} jobs")

    # Analyze job titles
    print("\n📋 Sample job titles (first 20):")
    for i, job in enumerate(jobs[:20], 1):
        title = job.get('title', '')
        location = job.get('location', '')
        print(f"  {i}. {title[:60]}")
        print(f"      Location: {location[:60]}")

    # Count locations
    print("\n📍 Location distribution:")
    locations = [job.get('location', '').split(',')[0].strip() for job in jobs if job.get('location')]
    location_counts = Counter(locations)
    for loc, count in location_counts.most_common(20):
        print(f"  {loc}: {count} jobs")

    # Check for our target keywords in titles
    print("\n🔍 Checking for keywords in titles:")
    keywords = ["Data Scientist", "Machine Learning", "Data Science"]
    for keyword in keywords:
        keyword_lower = keyword.lower()
        matches = [job for job in jobs if keyword_lower in job.get('title', '').lower()]
        print(f"  '{keyword}': {len(matches)} jobs")

        if matches:
            print(f"     Examples:")
            for job in matches[:3]:
                print(f"       - {job.get('title', '')} ({job.get('location', '')})")

    # Check for our target keywords in descriptions
    print("\n🔍 Checking for keywords in descriptions:")
    for keyword in keywords:
        keyword_lower = keyword.lower()
        matches = [job for job in jobs if keyword_lower in job.get('description', '').lower()]
        print(f"  '{keyword}': {len(matches)} jobs")

        if matches:
            print(f"     Examples:")
            for job in matches[:3]:
                print(f"       - {job.get('title', '')} ({job.get('location', '')})")

    # Check description quality
    print("\n📊 Description quality:")
    with_desc = [job for job in jobs if len(job.get('description', '')) > 200]
    print(f"  Jobs with good descriptions (>200 chars): {len(with_desc)}/{len(jobs)} ({len(with_desc)/len(jobs)*100:.1f}%)")

    avg_desc = sum(len(job.get('description', '')) for job in jobs) / len(jobs) if jobs else 0
    print(f"  Average description length: {avg_desc:.0f} chars")


if __name__ == "__main__":
    main()
