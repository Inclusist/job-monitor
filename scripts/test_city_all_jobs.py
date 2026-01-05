#!/usr/bin/env python3
"""
Test: Download ALL jobs in a city and do local matching

Strategy:
Instead of using API title filters (which are restrictive), fetch all jobs
in a city and match locally using:
- Keyword matching
- Semantic similarity
- Claude analysis

This could be more efficient and flexible than multiple filtered API calls.
"""

import os
import sys
import requests
from dotenv import load_dotenv
from collections import Counter
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

API_KEY = os.getenv('ACTIVEJOBS_API_KEY')
BASE_URL_24H = "https://active-jobs-db.p.rapidapi.com/active-ats-24h"
BASE_URL_7D = "https://active-jobs-db.p.rapidapi.com/active-ats-7d"

headers = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "active-jobs-db.p.rapidapi.com"
}

print("=" * 70)
print("CITY-WIDE JOB DOWNLOAD TEST")
print("=" * 70)

# Test with both 24h and 7-day to see difference
for window, endpoint in [("24h", BASE_URL_24H), ("7-day", BASE_URL_7D)]:
    print(f"\n{'='*70}")
    print(f"FETCHING ALL JOBS IN HAMBURG ({window} window)")
    print(f"{'='*70}")

    all_jobs = []
    page = 0

    while True:
        params = {
            'limit': 100,
            'offset': page * 100,
            'location_filter': 'Hamburg',
            'include_ai': 'true',
            'description_type': 'text'
        }

        print(f"\nFetching page {page + 1} (offset {params['offset']})...")
        response = requests.get(endpoint, headers=headers, params=params)

        if response.status_code != 200:
            print(f"❌ Error: Status {response.status_code}")
            break

        data = response.json()

        if not isinstance(data, list) or len(data) == 0:
            print(f"✓ No more jobs (end of results)")
            break

        all_jobs.extend(data)
        print(f"  Found {len(data)} jobs on this page")

        if len(data) < 100:
            print(f"✓ Last page (received {len(data)} < 100)")
            break

        page += 1

        # Safety limit
        if page >= 10:
            print(f"⚠️  Reached 10 pages limit (1000 jobs)")
            break

    print(f"\n{'='*70}")
    print(f"TOTAL: {len(all_jobs)} jobs in Hamburg ({window})")
    print(f"{'='*70}")

    if len(all_jobs) == 0:
        print("No jobs found, skipping analysis")
        continue

    # Analyze job titles
    print(f"\n📊 JOB ANALYSIS")
    print("-" * 70)

    # Extract keywords from titles
    keywords = []
    tech_keywords = []
    data_ml_keywords = []

    # Keywords we care about
    tech_terms = ['engineer', 'developer', 'software', 'data', 'machine learning',
                  'ml', 'ai', 'python', 'java', 'cloud', 'devops', 'backend',
                  'frontend', 'fullstack', 'full stack']

    data_ml_terms = ['data', 'machine learning', 'ml', 'ai', 'analytics',
                     'scientist', 'analyst', 'data engineer', 'ml engineer',
                     'ai engineer', 'deep learning', 'nlp']

    matching_jobs = []

    for job in all_jobs:
        title = job.get('title', '').lower()

        # Check for data/ML related jobs
        is_data_ml = any(term in title for term in data_ml_terms)

        if is_data_ml:
            matching_jobs.append(job)

        # Collect all words for analysis
        words = re.findall(r'\b\w+\b', title.lower())
        keywords.extend(words)

    # Show most common title words
    word_counts = Counter(keywords)
    print(f"\n🔤 Most Common Words in Job Titles (Top 20):")
    for word, count in word_counts.most_common(20):
        if len(word) > 3:  # Skip short words
            print(f"  {word}: {count}")

    # Show data/ML related jobs
    print(f"\n🎯 DATA/ML RELATED JOBS: {len(matching_jobs)}")
    print("-" * 70)
    if matching_jobs:
        print(f"\nFound {len(matching_jobs)} relevant jobs:")
        for i, job in enumerate(matching_jobs[:10], 1):
            print(f"\n{i}. {job.get('title', 'N/A')}")
            print(f"   Company: {job.get('organization', 'N/A')}")
            locations = job.get('locations_derived', [])
            print(f"   Location: {locations}")

            # Show AI fields
            ai_work = job.get('ai_work_arrangement_filter', 'N/A')
            ai_emp = job.get('ai_employment_type_filter', 'N/A')
            ai_exp = job.get('ai_experience_level_filter', 'N/A')
            print(f"   Work: {ai_work}, Type: {ai_emp}, Level: {ai_exp}")

        if len(matching_jobs) > 10:
            print(f"\n   ... and {len(matching_jobs) - 10} more")
    else:
        print("No data/ML jobs found")

    # Category breakdown
    print(f"\n📈 JOB CATEGORIES:")
    print("-" * 70)

    categories = {
        'Tech/Engineering': ['engineer', 'developer', 'software', 'devops', 'cloud'],
        'Data/ML/AI': ['data', 'machine learning', 'ml', 'ai', 'analytics', 'scientist'],
        'Management': ['manager', 'lead', 'director', 'head'],
        'Sales/Marketing': ['sales', 'marketing', 'business development'],
        'Healthcare': ['pflege', 'medizin', 'arzt', 'nurse', 'healthcare'],
        'Other': []
    }

    category_counts = {cat: 0 for cat in categories}

    for job in all_jobs:
        title = job.get('title', '').lower()
        categorized = False

        for category, terms in categories.items():
            if category == 'Other':
                continue
            if any(term in title for term in terms):
                category_counts[category] += 1
                categorized = True
                break

        if not categorized:
            category_counts['Other'] += 1

    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(all_jobs)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")

print("\n" + "=" * 70)
print("💡 INSIGHTS & RECOMMENDATIONS")
print("=" * 70)
print("""
STRATEGY COMPARISON:

CURRENT (Title Filtering):
- Multiple API calls per user query
- Complex syntax (phrases, operators)
- Often returns 0 results (too restrictive)
- Hard to debug when filters fail

ALTERNATIVE (City-Wide Download):
- One API call per city (Hamburg, Berlin, Munich, etc.)
- Download ALL jobs, match locally
- More flexible matching (keywords, semantic, Claude)
- Better visibility into what jobs are actually available

RECOMMENDATION:
If Data/ML jobs found in Hamburg:
→ City-wide download is more efficient
→ Can match multiple user profiles from same dataset
→ More control over matching logic

If very few relevant jobs found:
→ Current approach might be better
→ API filtering reduces unnecessary data transfer
""")
print("=" * 70)
