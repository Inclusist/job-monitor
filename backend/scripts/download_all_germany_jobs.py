#!/usr/bin/env python3
"""
Download ALL jobs in Germany from Active Jobs DB (last 7 days)

This downloads every job posting in Germany without any filtering,
storing them in raw_jobs_test for custom matching experiments.
"""
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

from src.collectors.activejobs import ActiveJobsCollector

def store_jobs_batch(conn, jobs_batch, raw_jobs_batch):
    """Store a batch of jobs in raw_jobs_test table with ALL AI metadata

    Args:
        conn: Database connection
        jobs_batch: List of parsed job dictionaries
        raw_jobs_batch: List of raw API response dictionaries
    """
    if not jobs_batch:
        return 0

    cursor = conn.cursor()

    # Prepare data for batch insert
    values = []
    skipped = 0
    for idx, job in enumerate(jobs_batch):
        try:
            raw_job = raw_jobs_batch[idx] if idx < len(raw_jobs_batch) else {}

            # Parse posted_date
            posted_date = job.get('posted_date')
            if isinstance(posted_date, str):
                try:
                    from datetime import datetime
                    posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                except:
                    posted_date = None

            # Parse date_validthrough
            date_validthrough = raw_job.get('date_validthrough')
            if isinstance(date_validthrough, str):
                try:
                    from datetime import datetime
                    date_validthrough = datetime.fromisoformat(date_validthrough.replace('Z', '+00:00'))
                except:
                    date_validthrough = None

            # Helper to safely get list fields
            def get_list(data, key, default=None):
                val = data.get(key, default)
                return val if isinstance(val, list) else default

            # Helper to safely get numeric fields
            def get_numeric(data, key, default=None):
                val = data.get(key)
                if val is None:
                    return default
                try:
                    return float(val) if isinstance(val, (int, float)) else default
                except:
                    return default

            # Extract location arrays
            locations_derived = get_list(raw_job, 'locations_derived', [])
            cities_derived = get_list(raw_job, 'cities_derived', [])
            regions_derived = get_list(raw_job, 'regions_derived', [])
            counties_derived = get_list(raw_job, 'counties_derived', [])
            countries_derived = get_list(raw_job, 'countries_derived', [])
            timezones_derived = get_list(raw_job, 'timezones_derived', [])
            lats_derived = get_list(raw_job, 'lats_derived', [])
            lngs_derived = get_list(raw_job, 'lngs_derived', [])

            # Extract AI metadata - Basic
            ai_employment_type = get_list(raw_job, 'ai_employment_type', [])
            ai_work_arrangement = raw_job.get('ai_work_arrangement')
            ai_experience_level = raw_job.get('ai_experience_level')
            ai_job_language = raw_job.get('ai_job_language')
            ai_visa_sponsorship = raw_job.get('ai_visa_sponsorship')
            ai_work_arrangement_office_days = get_numeric(raw_job, 'ai_work_arrangement_office_days')
            ai_working_hours = get_numeric(raw_job, 'ai_working_hours')

            # Extract AI metadata - Skills & Requirements
            ai_key_skills = get_list(raw_job, 'ai_key_skills', [])
            ai_keywords = get_list(raw_job, 'ai_keywords', [])
            ai_core_responsibilities = raw_job.get('ai_core_responsibilities')
            ai_requirements_summary = raw_job.get('ai_requirements_summary')
            ai_education_requirements = raw_job.get('ai_education_requirements')

            # Extract AI metadata - Benefits & Compensation
            ai_benefits = get_list(raw_job, 'ai_benefits', [])
            ai_salary_currency = raw_job.get('ai_salary_currency')
            ai_salary_minvalue = get_numeric(raw_job, 'ai_salary_minvalue')
            ai_salary_maxvalue = get_numeric(raw_job, 'ai_salary_maxvalue')
            ai_salary_value = get_numeric(raw_job, 'ai_salary_value')
            ai_salary_unittext = raw_job.get('ai_salary_unittext')

            # Extract AI metadata - Industry & Taxonomy
            ai_taxonomies_a = get_list(raw_job, 'ai_taxonomies_a', [])

            # Extract AI metadata - Remote/Location
            ai_remote_location = get_list(raw_job, 'ai_remote_location', [])
            ai_remote_location_derived = get_list(raw_job, 'ai_remote_location_derived', [])

            # Extract AI metadata - Hiring Manager
            ai_hiring_manager_name = raw_job.get('ai_hiring_manager_name')
            ai_hiring_manager_email_address = raw_job.get('ai_hiring_manager_email_address')

            values.append((
                # Core job fields
                raw_job.get('id'),  # external_id
                raw_job.get('title'),
                raw_job.get('organization'),  # company
                job.get('location') or '',  # Formatted location string from parser (ensure not None)
                raw_job.get('description_text') or raw_job.get('description_html', ''),
                raw_job.get('url'),
                raw_job.get('source'),
                raw_job.get('source_domain'),
                raw_job.get('source_type'),

                # Dates
                posted_date,
                date_validthrough,

                # Employment details
                job.get('salary'),  # Formatted salary from parser
                job.get('employment_type') or '',  # Formatted employment type from parser (ensure not None)
                raw_job.get('remote_derived', False),

                # Organization details
                raw_job.get('organization_url'),
                raw_job.get('organization_logo'),

                # Location arrays
                locations_derived,
                cities_derived,
                regions_derived,
                counties_derived,
                countries_derived,
                timezones_derived,
                lats_derived,
                lngs_derived,

                # AI-extracted metadata - Basic
                ai_employment_type,
                ai_work_arrangement,
                ai_experience_level,
                ai_job_language,
                ai_visa_sponsorship,
                ai_work_arrangement_office_days,
                ai_working_hours,

                # AI-extracted metadata - Skills & Requirements
                ai_key_skills,
                ai_keywords,
                ai_core_responsibilities,
                ai_requirements_summary,
                ai_education_requirements,

                # AI-extracted metadata - Benefits & Compensation
                ai_benefits,
                ai_salary_currency,
                ai_salary_minvalue,
                ai_salary_maxvalue,
                ai_salary_value,
                ai_salary_unittext,

                # AI-extracted metadata - Industry & Taxonomy
                ai_taxonomies_a,

                # AI-extracted metadata - Remote/Location
                ai_remote_location,
                ai_remote_location_derived,

                # AI-extracted metadata - Hiring Manager
                ai_hiring_manager_name,
                ai_hiring_manager_email_address,

                # Raw API response
                json.dumps(raw_job)
            ))
        except Exception as e:
            print(f"  ⚠️ Error preparing job {raw_job.get('id', 'unknown')} for insertion: {e}")
            skipped += 1
            continue

    if skipped > 0:
        print(f"  Skipped {skipped} jobs due to data errors")

    # Batch insert with ON CONFLICT DO NOTHING to skip duplicates
    query = """
        INSERT INTO raw_jobs_test (
            external_id, title, company, location, description, url, source,
            source_domain, source_type,
            posted_date, date_validthrough,
            salary, employment_type, remote,
            organization_url, organization_logo,
            locations_derived, cities_derived, regions_derived, counties_derived,
            countries_derived, timezones_derived, lats_derived, lngs_derived,
            ai_employment_type, ai_work_arrangement, ai_experience_level, ai_job_language,
            ai_visa_sponsorship, ai_work_arrangement_office_days, ai_working_hours,
            ai_key_skills, ai_keywords, ai_core_responsibilities, ai_requirements_summary,
            ai_education_requirements,
            ai_benefits, ai_salary_currency, ai_salary_minvalue, ai_salary_maxvalue,
            ai_salary_value, ai_salary_unittext,
            ai_taxonomies_a,
            ai_remote_location, ai_remote_location_derived,
            ai_hiring_manager_name, ai_hiring_manager_email_address,
            raw_data
        ) VALUES %s
        ON CONFLICT (external_id) DO NOTHING
    """

    try:
        execute_values(cursor, query, values)
        conn.commit()
        inserted = cursor.rowcount
        cursor.close()
        return inserted
    except Exception as e:
        print(f"  ⚠️ Error inserting batch: {e}")
        conn.rollback()
        cursor.close()
        return 0


def download_all_jobs(max_pages=500, start_page=0):
    """Download all jobs from Germany (7-day window)

    Args:
        max_pages: Maximum number of pages to fetch (each page = 100 jobs)
        start_page: Starting page number (for offset)
    """
    print("=" * 80)
    print("DOWNLOADING ALL JOBS FROM GERMANY (LAST 7 DAYS)")
    print("=" * 80)
    print(f"Pages to fetch: {max_pages} (starting from page {start_page})")
    print(f"Offset: {start_page * 100}, Limit per page: 100")

    # Check if table exists
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'raw_jobs_test'
        )
    """)
    table_exists = cursor.fetchone()[0]
    cursor.close()

    if not table_exists:
        print("\n❌ Table raw_jobs_test does not exist!")
        print("Run: python scripts/create_raw_jobs_table.py")
        conn.close()
        return

    # Initialize Active Jobs collector
    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    if not api_key:
        print("❌ ACTIVEJOBS_API_KEY not set!")
        conn.close()
        return

    collector = ActiveJobsCollector(
        api_key=api_key,
        enable_filtering=False,  # No filtering - get everything!
        min_quality=1
    )

    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nFetching ALL jobs in Germany from last 7 days...")
    print("No filters - downloading complete dataset")
    print()

    # Download jobs with pagination
    # Note: We'll manually handle pagination to support offset
    import requests

    endpoint = f"{collector.base_url}/active-ats-7d"
    all_jobs = []
    all_raw_jobs = []  # Keep raw API responses

    for page_idx in range(max_pages):
        page_num = start_page + page_idx
        offset = page_num * 100

        params = {
            'limit': 100,
            'offset': offset,
            'location_filter': 'Germany',
            'description_type': 'text',
            'include_ai': 'true'
        }

        print(f"\nFetching page {page_num + 1} (offset {offset})...")

        try:
            response = requests.get(endpoint, headers=collector.headers, params=params)

            if response.status_code == 429:
                print("  ⚠️ Rate limit hit!")
                break

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                jobs_data = data
            else:
                jobs_data = data.get('data', [])

            if not jobs_data:
                print(f"  No more results")
                break

            # Parse jobs and keep raw responses
            for job in jobs_data:
                try:
                    all_raw_jobs.append(job)  # Store raw API response
                    all_jobs.append(collector._parse_job(job))  # Store parsed job
                except Exception as e:
                    print(f"  ⚠️ Error parsing job {job.get('id', 'unknown')}: {e}")
                    # Remove the raw job we just added
                    if all_raw_jobs and all_raw_jobs[-1] == job:
                        all_raw_jobs.pop()
                    continue

            print(f"  ✓ Found {len(jobs_data)} jobs (total: {len(all_jobs)})")

            # Check quota
            jobs_remaining = response.headers.get('x-ratelimit-jobs-remaining')
            requests_remaining = response.headers.get('x-ratelimit-requests-remaining')
            if jobs_remaining:
                print(f"  Quota: {jobs_remaining} jobs, {requests_remaining} requests remaining")

            # If we got fewer than 100, we've reached the end
            if len(jobs_data) < 100:
                print(f"  Reached end of results")
                break

        except Exception as e:
            print(f"  ❌ Error: {e}")
            break

    print(f"\n{'='*80}")
    print(f"DOWNLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"Total jobs fetched: {len(all_jobs)}")

    if not all_jobs:
        print("No jobs found!")
        conn.close()
        return

    # Store in batches of 1000
    print(f"\nStoring jobs in database (batch size: 1000)...")
    batch_size = 1000
    total_inserted = 0

    for i in range(0, len(all_jobs), batch_size):
        jobs_batch = all_jobs[i:i+batch_size]
        raw_batch = all_raw_jobs[i:i+batch_size]
        inserted = store_jobs_batch(conn, jobs_batch, raw_batch)
        total_inserted += inserted
        print(f"  Batch {i//batch_size + 1}: {inserted}/{len(jobs_batch)} inserted (total: {total_inserted})")

    conn.close()

    print(f"\n{'='*80}")
    print(f"STORAGE COMPLETE")
    print(f"{'='*80}")
    print(f"Total jobs stored: {total_inserted}/{len(all_jobs)}")
    print(f"Duplicates skipped: {len(all_jobs) - total_inserted}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Show summary stats
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM raw_jobs_test")
    total = cursor.fetchone()[0]

    # Show top industries (ai_taxonomies_a is an array, use UNNEST)
    cursor.execute("""
        SELECT industry, COUNT(*) as count
        FROM raw_jobs_test, UNNEST(ai_taxonomies_a) as industry
        WHERE industry IS NOT NULL AND industry != ''
        GROUP BY industry
        ORDER BY count DESC
        LIMIT 10
    """)

    print("Top 10 Industries:")
    print("-" * 60)
    for industry, count in cursor.fetchall():
        print(f"  {industry}: {count}")

    # Show experience levels (ai_experience_level is a string)
    cursor.execute("""
        SELECT ai_experience_level, COUNT(*) as count
        FROM raw_jobs_test
        WHERE ai_experience_level IS NOT NULL AND ai_experience_level != ''
        GROUP BY ai_experience_level
        ORDER BY count DESC
    """)

    print("\nExperience Levels:")
    print("-" * 60)
    for level, count in cursor.fetchall():
        print(f"  {level}: {count}")

    # Show work arrangements
    cursor.execute("""
        SELECT ai_work_arrangement, COUNT(*) as count
        FROM raw_jobs_test
        WHERE ai_work_arrangement IS NOT NULL AND ai_work_arrangement != ''
        GROUP BY ai_work_arrangement
        ORDER BY count DESC
    """)

    print("\nWork Arrangements:")
    print("-" * 60)
    for arrangement, count in cursor.fetchall():
        print(f"  {arrangement}: {count}")

    # Show top skills (ai_key_skills is an array)
    cursor.execute("""
        SELECT skill, COUNT(*) as count
        FROM raw_jobs_test, UNNEST(ai_key_skills) as skill
        WHERE skill IS NOT NULL AND skill != ''
        GROUP BY skill
        ORDER BY count DESC
        LIMIT 15
    """)

    print("\nTop 15 Skills:")
    print("-" * 60)
    for skill, count in cursor.fetchall():
        print(f"  {skill}: {count}")

    cursor.close()
    conn.close()

    print(f"\n✓ Done! {total} jobs ready for custom matching")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Download jobs from Active Jobs DB')
    parser.add_argument('--max-pages', type=int, default=1,
                        help='Number of pages to fetch (default: 1, each page = 100 jobs)')
    parser.add_argument('--start-page', type=int, default=0,
                        help='Starting page number for offset (default: 0)')

    args = parser.parse_args()

    download_all_jobs(max_pages=args.max_pages, start_page=args.start_page)
