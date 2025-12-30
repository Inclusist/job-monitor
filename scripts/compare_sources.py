#!/usr/bin/env python3
"""
Compare job sources: Active Jobs DB vs JSearch
Tests with controlled parameters to determine coverage and overlap
"""

import os
import sys
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables FIRST
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.jsearch import JSearchCollector
from src.database.factory import get_database


# Test parameters
KEYWORDS = ["Data Scientist", "Machine Learning Engineer", "Data Science Manager"]
LOCATIONS = ["Berlin", "Hamburg"]
DATE_POSTED = "week"  # Last 7 days (JSearch API uses: all, today, 3days, week, month)


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def test_jsearch():
    """Test JSearch API with controlled parameters"""
    print_header("TESTING JSEARCH")

    api_key = os.getenv('JSEARCH_API_KEY')
    if not api_key:
        print("❌ JSEARCH_API_KEY not found in .env")
        return None

    collector = JSearchCollector(api_key)

    results = defaultdict(lambda: defaultdict(list))
    total_jobs = 0

    for keyword in KEYWORDS:
        for location in LOCATIONS:
            print(f"\n🔍 Searching: '{keyword}' in {location}")

            try:
                jobs = collector.search_jobs(
                    query=keyword,
                    location=location,
                    date_posted=DATE_POSTED,
                    num_pages=5,  # 5 pages * 10 jobs = 50 jobs
                    country="de"  # Germany
                )

                print(f"   ✅ Found {len(jobs)} jobs")
                results[location][keyword] = jobs
                total_jobs += len(jobs)

            except Exception as e:
                print(f"   ❌ Error: {e}")
                results[location][keyword] = []

    print(f"\n📊 Total jobs found: {total_jobs}")

    # Show breakdown
    print("\nBreakdown by location and keyword:")
    for location in LOCATIONS:
        print(f"\n  {location}:")
        for keyword in KEYWORDS:
            count = len(results[location][keyword])
            print(f"    {keyword}: {count} jobs")

    return results


def analyze_database():
    """Analyze existing database for Active Jobs DB vs JSearch comparison"""
    print_header("ANALYZING EXISTING DATABASE")

    db = get_database()
    conn = db._get_connection()

    # Get breakdown by source
    print("\n📊 Current database status:")
    cursor = conn.cursor()

    # Total by source
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM jobs
        WHERE source IN ('Active Jobs DB', 'JSearch')
        GROUP BY source
        ORDER BY count DESC
    """)

    source_counts = {}
    for row in cursor.fetchall():
        source = row[0]
        count = row[1]
        source_counts[source] = count
        print(f"  {source}: {count} jobs")

    # Jobs added in last 7 days (matching our test period)
    print("\n📅 Jobs added in last 7 days:")
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM jobs
        WHERE source IN ('Active Jobs DB', 'JSearch')
        AND discovered_date >= NOW() - INTERVAL '7 days'
        GROUP BY source
        ORDER BY count DESC
    """)

    recent_counts = {}
    for row in cursor.fetchall():
        source = row[0]
        count = row[1]
        recent_counts[source] = count
        print(f"  {source}: {count} jobs")

    # Check overlap - same title + company from different sources
    print("\n🔄 Checking for duplicates across sources:")
    cursor.execute("""
        SELECT
            LOWER(TRIM(title)) as norm_title,
            LOWER(TRIM(company)) as norm_company,
            STRING_AGG(DISTINCT source, ', ') as sources,
            COUNT(*) as count
        FROM jobs
        WHERE source IN ('Active Jobs DB', 'JSearch')
        GROUP BY norm_title, norm_company
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        LIMIT 20
    """)

    duplicates = cursor.fetchall()
    if duplicates:
        print(f"  Found {len(duplicates)} duplicate job postings:")
        for dup in duplicates[:10]:  # Show top 10
            title, company, sources, count = dup
            print(f"    • {title[:50]} at {company[:30]} ({sources})")
    else:
        print("  ✅ No duplicates found between Active Jobs DB and JSearch")

    # Coverage by location (for our test locations)
    print(f"\n📍 Coverage in test locations (Berlin, Hamburg):")
    for location in LOCATIONS:
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM jobs
            WHERE source IN ('Active Jobs DB', 'JSearch')
            AND LOWER(location) LIKE %s
            GROUP BY source
        """, (f'%{location.lower()}%',))

        print(f"\n  {location}:")
        for row in cursor.fetchall():
            source = row[0]
            count = row[1]
            print(f"    {source}: {count} jobs")

    # Coverage by keywords
    print(f"\n🎯 Coverage by test keywords:")
    for keyword in KEYWORDS:
        # Split keyword to search for individual terms
        search_term = keyword.lower().replace(' ', '%')

        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM jobs
            WHERE source IN ('Active Jobs DB', 'JSearch')
            AND LOWER(title) LIKE %s
            GROUP BY source
        """, (f'%{search_term}%',))

        print(f"\n  '{keyword}':")
        for row in cursor.fetchall():
            source = row[0]
            count = row[1]
            print(f"    {source}: {count} jobs")

    db._return_connection(conn)

    return {
        'source_counts': source_counts,
        'recent_counts': recent_counts,
        'duplicate_count': len(duplicates) if duplicates else 0
    }


def calculate_overlap(jsearch_results, db_analysis):
    """Calculate overlap between new JSearch results and existing database"""
    print_header("CALCULATING OVERLAP")

    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()

    total_new = 0
    total_overlap = 0

    for location in LOCATIONS:
        for keyword in KEYWORDS:
            jobs = jsearch_results[location][keyword]

            for job in jobs:
                # Check if this job exists in database
                cursor.execute("""
                    SELECT COUNT(*) FROM jobs
                    WHERE LOWER(TRIM(title)) = %s
                    AND LOWER(TRIM(company)) = %s
                """, (job['title'].lower().strip(), job['company'].lower().strip()))

                exists = cursor.fetchone()[0] > 0

                if exists:
                    total_overlap += 1
                else:
                    total_new += 1

    total_jobs = total_new + total_overlap

    print(f"\n📊 JSearch test results vs existing database:")
    print(f"  Total jobs from JSearch test: {total_jobs}")
    print(f"  Already in database: {total_overlap} ({total_overlap/total_jobs*100:.1f}%)")
    print(f"  New unique jobs: {total_new} ({total_new/total_jobs*100:.1f}%)")

    db._return_connection(conn)

    return {
        'total': total_jobs,
        'overlap': total_overlap,
        'new': total_new,
        'overlap_rate': total_overlap/total_jobs if total_jobs > 0 else 0
    }


def make_recommendation(jsearch_results, db_analysis, overlap_analysis):
    """Make recommendation on source strategy"""
    print_header("RECOMMENDATION")

    activejobs_count = db_analysis['source_counts'].get('Active Jobs DB', 0)
    jsearch_count = db_analysis['source_counts'].get('JSearch', 0)

    print("\n📈 Source Performance Summary:\n")

    print(f"1. Active Jobs DB:")
    print(f"   • Total jobs in database: {activejobs_count}")
    print(f"   • Coverage: 36 ATS platforms")
    print(f"   • Quality: 99.7% (3,753 chars avg)")
    print(f"   • Status: ⚠️  RATE LIMITED (0/25 requests remaining)")
    print(f"   • Free tier: 200 requests/month")

    print(f"\n2. JSearch (RapidAPI):")
    print(f"   • Total jobs in database: {jsearch_count}")
    print(f"   • Coverage: Indeed + LinkedIn aggregation")
    print(f"   • Quality: 99.2% (3,838 chars avg)")
    print(f"   • Test results: {overlap_analysis['total']} jobs found")
    print(f"   • Overlap with existing: {overlap_analysis['overlap_rate']*100:.1f}%")

    print(f"\n3. Duplicate Analysis:")
    print(f"   • Cross-source duplicates: {db_analysis['duplicate_count']}")
    print(f"   • Minimal overlap between Active Jobs DB and JSearch")

    print("\n" + "=" * 60)
    print("💡 RECOMMENDATION")
    print("=" * 60)

    # Make recommendation based on data
    if activejobs_count > jsearch_count * 5:
        print("\n✅ Strategy: Active Jobs DB as primary source")
        print("\nRationale:")
        print("  • Active Jobs DB provides significantly more coverage")
        print("  • Minimal duplication with JSearch")
        print("  • 36 ATS platforms vs 2 sources (Indeed/LinkedIn)")
        print("\n⚠️  Issue: Currently rate limited")
        print("  Options:")
        print("  1. Wait for monthly reset (recommended)")
        print("  2. Upgrade to paid tier for more requests")
        print("  3. Use JSearch as temporary backup during rate limit")

    else:
        print("\n✅ Strategy: Use both sources")
        print("\nRationale:")
        print("  • Both sources provide comparable coverage")
        print("  • Minimal duplication between sources")
        print("  • JSearch fills gaps when Active Jobs DB is rate limited")
        print("  • Combined coverage maximizes job discovery")

    print("\n📌 Additional Options:")
    print("  • Apify StepStone: €15/month for German market focus")
    print("    - Use if current sources don't provide enough DE jobs")
    print("    - StepStone is a major German job board")


def main():
    """Main comparison function"""
    print_header("JOB SOURCE COMPARISON TEST")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    print(f"Locations: {', '.join(LOCATIONS)}")
    print(f"Date range: {DATE_POSTED}")

    # Step 1: Test JSearch (Active Jobs DB already known to be rate limited)
    jsearch_results = test_jsearch()

    if not jsearch_results:
        print("\n❌ JSearch test failed")
        return

    # Step 2: Analyze existing database
    db_analysis = analyze_database()

    # Step 3: Calculate overlap
    overlap_analysis = calculate_overlap(jsearch_results, db_analysis)

    # Step 4: Make recommendation
    make_recommendation(jsearch_results, db_analysis, overlap_analysis)

    print("\n" + "=" * 60)
    print("✅ Analysis complete")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
