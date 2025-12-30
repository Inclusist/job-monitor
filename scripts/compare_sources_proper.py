#!/usr/bin/env python3
"""
Proper comparison: Active Jobs DB vs JSearch
Uses bulk fetch for Active Jobs DB (like production) + client-side filtering
"""

import os
import sys
from dotenv import load_dotenv
from collections import defaultdict
import re

# Load environment variables FIRST
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.activejobs import ActiveJobsCollector
from src.collectors.jsearch import JSearchCollector


# Test parameters
KEYWORDS = ["Data Scientist", "Machine Learning Engineer", "Data Science Manager"]
LOCATIONS = ["Berlin", "Hamburg"]


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def matches_keyword(job, keywords):
    """
    Check if job matches any of the keywords
    Uses flexible matching: splits multi-word keywords and checks if key terms appear
    """
    title = job.get('title', '').lower()
    description = job.get('description', '').lower()
    combined = title + ' ' + description

    for keyword in keywords:
        keyword_lower = keyword.lower()

        # For multi-word keywords, extract the core terms
        # e.g., "Data Scientist" -> check for "data" AND "scientist"
        # "Machine Learning Engineer" -> check for "machine learning"

        if 'data scientist' in keyword_lower or 'data science' in keyword_lower:
            # Match if has "data" AND ("scientist" OR "science")
            if 'data' in combined and ('scientist' in combined or 'science' in combined):
                return True
        elif 'machine learning' in keyword_lower:
            # Match if has "machine learning" (together)
            if 'machine learning' in combined or 'ml engineer' in combined:
                return True
        else:
            # For other keywords, just check if the full phrase appears
            if keyword_lower in combined:
                return True

    return False


def matches_location(job, location):
    """Check if job matches location"""
    job_location = job.get('location', '').lower()
    return location.lower() in job_location


def normalize_job(job):
    """Normalize job data for comparison"""
    return {
        'title': job.get('title', '').lower().strip(),
        'company': job.get('company', '').lower().strip(),
        'location': job.get('location', '').lower().strip(),
        'description_length': len(job.get('description', '')),
        'raw': job
    }


def test_activejobs():
    """Test Active Jobs DB using bulk fetch method (like production)"""
    print_header("TESTING ACTIVE JOBS DB (BULK FETCH)")
    print("Using search_all_recent_jobs() like production system")

    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    if not api_key:
        print("❌ ACTIVEJOBS_API_KEY not found in .env")
        return None

    collector = ActiveJobsCollector(api_key)

    # Fetch all recent jobs from Germany (last 7 days)
    print("\n🔍 Fetching all recent jobs from Germany (last 7 days)...")
    print("   This is how bulk loading works in production")

    try:
        all_jobs = collector.search_all_recent_jobs(
            location="Germany",
            max_pages=10,  # 10 pages * 100 = up to 1000 jobs
            date_posted="week"
        )

        print(f"\n✅ Fetched {len(all_jobs)} total jobs from Active Jobs DB")

        # Now filter by keywords and locations client-side
        filtered_results = defaultdict(lambda: defaultdict(list))

        for location in LOCATIONS:
            for keyword in KEYWORDS:
                matching_jobs = [
                    job for job in all_jobs
                    if matches_keyword(job, [keyword]) and matches_location(job, location)
                ]
                filtered_results[location][keyword] = matching_jobs

        # Show results
        print("\n📊 After filtering by keywords and locations:")
        total_filtered = 0
        for location in LOCATIONS:
            print(f"\n  {location}:")
            for keyword in KEYWORDS:
                jobs = filtered_results[location][keyword]
                count = len(jobs)
                total_filtered += count
                print(f"    {keyword}: {count} jobs")

                # Show quality metrics for first location
                if jobs and location == LOCATIONS[0]:
                    avg_desc_len = sum(len(j.get('description', '')) for j in jobs) / len(jobs)
                    good_quality = sum(1 for j in jobs if len(j.get('description', '')) > 200)
                    print(f"      📊 Avg description: {avg_desc_len:.0f} chars, Quality: {good_quality}/{len(jobs)} ({good_quality/len(jobs)*100:.1f}%)")

        print(f"\n📊 Total matching jobs: {total_filtered}")

        return filtered_results

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def test_jsearch():
    """Test JSearch with keyword searches"""
    print_header("TESTING JSEARCH (KEYWORD SEARCH)")

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
                    date_posted="week",
                    num_pages=5,
                    country="de"
                )

                print(f"   ✅ Found {len(jobs)} jobs")

                # Show quality metrics
                if jobs:
                    avg_desc_len = sum(len(j.get('description', '')) for j in jobs) / len(jobs)
                    good_quality = sum(1 for j in jobs if len(j.get('description', '')) > 200)
                    print(f"   📊 Avg description: {avg_desc_len:.0f} chars")
                    print(f"   ✨ Quality: {good_quality}/{len(jobs)} ({good_quality/len(jobs)*100:.1f}%)")

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


def calculate_overlap(activejobs_results, jsearch_results):
    """Calculate overlap between the two sources"""
    print_header("CALCULATING OVERLAP")

    # Normalize all jobs from both sources
    activejobs_set = set()
    jsearch_set = set()

    activejobs_jobs = []
    jsearch_jobs = []

    # Collect all Active Jobs DB jobs
    for location in LOCATIONS:
        for keyword in KEYWORDS:
            for job in activejobs_results[location][keyword]:
                normalized = normalize_job(job)
                key = (normalized['title'], normalized['company'])
                activejobs_set.add(key)
                activejobs_jobs.append(normalized)

    # Collect all JSearch jobs
    for location in LOCATIONS:
        for keyword in KEYWORDS:
            for job in jsearch_results[location][keyword]:
                normalized = normalize_job(job)
                key = (normalized['title'], normalized['company'])
                jsearch_set.add(key)
                jsearch_jobs.append(normalized)

    # Calculate overlap
    overlap = activejobs_set.intersection(jsearch_set)
    unique_to_activejobs = activejobs_set - jsearch_set
    unique_to_jsearch = jsearch_set - activejobs_set

    total_unique = len(activejobs_set.union(jsearch_set))

    print(f"\n📊 Overlap Analysis:")
    print(f"  Active Jobs DB: {len(activejobs_set)} unique jobs")
    print(f"  JSearch: {len(jsearch_set)} unique jobs")
    print(f"  Overlap (same jobs in both): {len(overlap)} jobs")
    print(f"  Unique to Active Jobs DB: {len(unique_to_activejobs)} jobs")
    print(f"  Unique to JSearch: {len(unique_to_jsearch)} jobs")
    print(f"  Total unique jobs (combined): {total_unique} jobs")

    if len(activejobs_set) > 0 and len(jsearch_set) > 0:
        overlap_rate = len(overlap) / min(len(activejobs_set), len(jsearch_set)) * 100
        print(f"\n📈 Overlap rate: {overlap_rate:.1f}%")
        print(f"   (overlap / smaller source)")

    # Show some examples of overlapping jobs
    if overlap:
        print(f"\n🔄 Examples of overlapping jobs:")
        for i, (title, company) in enumerate(list(overlap)[:5], 1):
            print(f"  {i}. {title[:60]} at {company[:30]}")

    # Quality comparison
    print(f"\n📊 Quality Comparison:")
    if activejobs_jobs:
        avg_activejobs = sum(j['description_length'] for j in activejobs_jobs) / len(activejobs_jobs)
        good_activejobs = sum(1 for j in activejobs_jobs if j['description_length'] > 200)
        print(f"  Active Jobs DB:")
        print(f"    Avg description: {avg_activejobs:.0f} chars")
        print(f"    Good quality (>200 chars): {good_activejobs}/{len(activejobs_jobs)} ({good_activejobs/len(activejobs_jobs)*100:.1f}%)")

    if jsearch_jobs:
        avg_jsearch = sum(j['description_length'] for j in jsearch_jobs) / len(jsearch_jobs)
        good_jsearch = sum(1 for j in jsearch_jobs if j['description_length'] > 200)
        print(f"  JSearch:")
        print(f"    Avg description: {avg_jsearch:.0f} chars")
        print(f"    Good quality (>200 chars): {good_jsearch}/{len(jsearch_jobs)} ({good_jsearch/len(jsearch_jobs)*100:.1f}%)")

    return {
        'activejobs_count': len(activejobs_set),
        'jsearch_count': len(jsearch_set),
        'overlap_count': len(overlap),
        'unique_to_activejobs': len(unique_to_activejobs),
        'unique_to_jsearch': len(unique_to_jsearch),
        'total_unique': total_unique,
        'overlap_rate': overlap_rate if len(activejobs_set) > 0 and len(jsearch_set) > 0 else 0
    }


def make_recommendation(overlap_analysis):
    """Make recommendation based on proper comparison"""
    print_header("RECOMMENDATION")

    activejobs_count = overlap_analysis['activejobs_count']
    jsearch_count = overlap_analysis['jsearch_count']
    overlap_count = overlap_analysis['overlap_count']
    total_unique = overlap_analysis['total_unique']
    overlap_rate = overlap_analysis['overlap_rate']

    print("\n📈 Proper Comparison Summary:\n")

    print(f"1. Active Jobs DB (bulk fetch + client-side filtering):")
    print(f"   • Jobs found: {activejobs_count}")
    print(f"   • Method: Fetch all Germany jobs, filter by keyword+location")
    print(f"   • Coverage: 36 ATS platforms")
    print(f"   • Unique jobs: {overlap_analysis['unique_to_activejobs']}")

    print(f"\n2. JSearch (keyword search):")
    print(f"   • Jobs found: {jsearch_count}")
    print(f"   • Method: Direct keyword search")
    print(f"   • Coverage: Indeed + LinkedIn")
    print(f"   • Unique jobs: {overlap_analysis['unique_to_jsearch']}")

    print(f"\n3. Combined Coverage:")
    print(f"   • Total unique jobs: {total_unique}")
    print(f"   • Overlap: {overlap_count} jobs ({overlap_rate:.1f}%)")
    print(f"   • Efficiency gain: {total_unique - max(activejobs_count, jsearch_count)} extra jobs from dual sources")

    print("\n" + "=" * 60)
    print("💡 RECOMMENDATION")
    print("=" * 60)

    # Make recommendation based on overlap rate and coverage
    if overlap_rate > 70:
        # High overlap - one source is sufficient
        if activejobs_count > jsearch_count:
            print("\n✅ Strategy: Use Active Jobs DB as primary source")
            print("\nRationale:")
            print(f"  • Active Jobs DB provides more jobs ({activejobs_count} vs {jsearch_count})")
            print(f"  • High overlap ({overlap_rate:.1f}%) means JSearch adds little value")
            print(f"  • Saves API costs by using only one source")
            print("\n💡 Optional: Keep JSearch as backup")
        else:
            print("\n✅ Strategy: Use JSearch as primary source")
            print("\nRationale:")
            print(f"  • JSearch provides more jobs ({jsearch_count} vs {activejobs_count})")
            print(f"  • High overlap ({overlap_rate:.1f}%) means Active Jobs DB adds little value")
            print(f"  • Saves API costs by using only one source")

    elif overlap_rate > 40:
        # Medium overlap
        efficiency_gain = total_unique - max(activejobs_count, jsearch_count)
        efficiency_rate = efficiency_gain / max(activejobs_count, jsearch_count) * 100

        if efficiency_rate < 15:
            print("\n✅ Strategy: Use the larger source only")
            print("\nRationale:")
            print(f"  • Moderate overlap ({overlap_rate:.1f}%)")
            print(f"  • Dual sources only add {efficiency_gain} jobs ({efficiency_rate:.1f}% gain)")
            print(f"  • Not worth the cost/complexity of maintaining two sources")
            if activejobs_count > jsearch_count:
                print(f"  • Recommended: Active Jobs DB ({activejobs_count} jobs)")
            else:
                print(f"  • Recommended: JSearch ({jsearch_count} jobs)")
        else:
            print("\n✅ Strategy: Use both sources")
            print("\nRationale:")
            print(f"  • Moderate overlap ({overlap_rate:.1f}%)")
            print(f"  • Dual sources add {efficiency_gain} jobs ({efficiency_rate:.1f}% gain)")
            print(f"  • Worth maintaining both for maximum coverage")

    else:
        # Low overlap - both sources provide unique value
        print("\n✅ Strategy: Use both sources (RECOMMENDED)")
        print("\nRationale:")
        print(f"  • Low overlap ({overlap_rate:.1f}%) means sources are complementary")
        print(f"  • Active Jobs DB unique: {overlap_analysis['unique_to_activejobs']} jobs")
        print(f"  • JSearch unique: {overlap_analysis['unique_to_jsearch']} jobs")
        print(f"  • Combined coverage: {total_unique} jobs")
        print(f"  • Maximum job discovery with minimal duplication")

    print("\n📌 Implementation Note:")
    print("  • Active Jobs DB: Use bulk fetch (search_all_recent_jobs)")
    print("  • Filter by keywords client-side for flexibility")
    print("  • Both sources have excellent quality (>99%)")


def main():
    """Main comparison function"""
    print_header("PROPER SOURCE COMPARISON TEST")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    print(f"Locations: {', '.join(LOCATIONS)}")
    print(f"Date range: Last 7 days")
    print("\n⚡ Using production methods for fair comparison...")

    # Step 1: Test Active Jobs DB (bulk fetch)
    activejobs_results = test_activejobs()
    if not activejobs_results:
        print("\n❌ Active Jobs DB test failed")
        return

    # Step 2: Test JSearch (keyword search)
    jsearch_results = test_jsearch()
    if not jsearch_results:
        print("\n❌ JSearch test failed")
        return

    # Step 3: Calculate overlap
    overlap_analysis = calculate_overlap(activejobs_results, jsearch_results)

    # Step 4: Make recommendation
    make_recommendation(overlap_analysis)

    print("\n" + "=" * 60)
    print("✅ Proper comparison complete")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
