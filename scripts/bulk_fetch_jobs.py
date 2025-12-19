#!/usr/bin/env python3
"""
Standalone script to bulk fetch jobs from Active Jobs DB and store in database
Reads configuration from config.yaml for countries, locations, and remote settings
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from collectors.activejobs import ActiveJobsCollector
from database.operations import JobDatabase
from utils.helpers import deduplicate_jobs, filter_new_jobs

# Load environment variables
load_dotenv()


def load_bulk_config():
    """Load bulk fetch configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    
    if not config_path.exists():
        print(f"⚠️  config.yaml not found at {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config.get('bulk_fetch', {})


def fetch_and_store_jobs(max_jobs=None, date_posted=None, locations=None, 
                         include_remote=None, test_mode=True):
    """
    Fetch jobs from Active Jobs DB and store in database
    
    Args:
        max_jobs: Maximum number of jobs to fetch (overrides config)
        date_posted: '24h' or 'week' (overrides config)
        locations: List of locations to search (overrides config)
        include_remote: Include remote jobs (overrides config)
        test_mode: If True, only show what would be done without storing
    """
    print("="*70)
    print("🔍 Bulk Job Fetching Script")
    print("="*70)
    
    # Load config
    bulk_config = load_bulk_config()
    
    # Use config values as defaults
    if bulk_config:
        max_jobs = max_jobs or bulk_config.get('max_jobs', 1000)
        date_posted = date_posted or bulk_config.get('date_posted', '24h')
        
        # Combine countries and locations
        config_locations = []
        config_locations.extend(bulk_config.get('countries', []))
        config_locations.extend(bulk_config.get('locations', []))
        locations = locations or config_locations or ['Germany']
        
        include_remote = include_remote if include_remote is not None else bulk_config.get('include_remote', False)
    else:
        max_jobs = max_jobs or 1000
        date_posted = date_posted or '24h'
        locations = locations or ['Germany']
        include_remote = include_remote if include_remote is not None else False
    
    # Initialize
    activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')
    user_email = os.getenv('USER_EMAIL', 'default@localhost')
    
    if not activejobs_key:
        print("❌ Error: ACTIVEJOBS_API_KEY not found in .env")
        return
    
    print(f"📧 User: {user_email}")
    print(f"📊 Mode: {'TEST (no storage)' if test_mode else 'PRODUCTION (will store)'}")
    print(f"🎯 Max jobs: {max_jobs}")
    print(f"📅 Date posted: {date_posted}")
    print(f"📍 Locations: {', '.join(locations)}")
    print(f"🏠 Include remote: {include_remote}")
    print()
    
    # Initialize collector
    collector = ActiveJobsCollector(activejobs_key)
    
    # Collect jobs from all locations
    all_jobs = []
    
    # Calculate pages per location
    jobs_per_location = max_jobs // len(locations) if locations else max_jobs
    max_pages_per_location = (jobs_per_location // 100) + (1 if jobs_per_location % 100 else 0)
    
    # Fetch from each location
    for location in locations:
        print(f"📥 Fetching from {location}...")
        jobs = collector.search_all_recent_jobs(
            location=location,
            max_pages=max_pages_per_location,
            date_posted=date_posted
        )
        print(f"   ✅ Found {len(jobs)} jobs in {location}")
        all_jobs.extend(jobs)
    
    # Fetch remote jobs if enabled
    if include_remote:
        print(f"📥 Fetching remote jobs...")
        remote_jobs = collector.search_all_recent_jobs(
            location=None,  # No location filter for remote
            max_pages=max_pages_per_location,
            date_posted=date_posted,
            remote_only=True
        )
        print(f"   ✅ Found {len(remote_jobs)} remote jobs")
        all_jobs.extend(remote_jobs)
    
    print()
    print(f"✅ Fetched {len(all_jobs)} jobs")
    
    if not all_jobs:
        print("❌ No jobs fetched. Exiting.")
        return
    
    # Deduplicate
    print()
    print("🔄 Removing duplicates...")
    unique_jobs = deduplicate_jobs(all_jobs)
    print(f"✅ {len(unique_jobs)} unique jobs (removed {len(all_jobs) - len(unique_jobs)} duplicates)")
    
    if test_mode:
        print()
        print("="*70)
        print("🧪 TEST MODE - Jobs would be stored but NOT storing now")
        print("="*70)
        print(f"Total unique jobs ready: {len(unique_jobs)}")
        print()
        print("Sample jobs:")
        for i, job in enumerate(unique_jobs[:5], 1):
            print(f"{i}. {job.get('title')} at {job.get('company')} - {job.get('location')}")
        print()
        print("To actually store these jobs, run with test_mode=False")
        return unique_jobs
    
    # Store in database
    print()
    print("💾 Connecting to database...")
    job_db = JobDatabase()
    
    print("🔍 Filtering new jobs (not already in database)...")
    new_jobs = filter_new_jobs(unique_jobs, job_db)
    print(f"✅ {len(new_jobs)} new jobs to store (skipping {len(unique_jobs) - len(new_jobs)} already in DB)")
    
    if not new_jobs:
        print()
        print("✅ No new jobs to store. All jobs already in database.")
        return unique_jobs
    
    # Store jobs
    print()
    print(f"💾 Storing {len(new_jobs)} jobs in database...")
    stored_count = 0
    
    for i, job in enumerate(new_jobs, 1):
        try:
            # Prepare job data for database
            job_data = {
                'external_id': job.get('external_id'),
                'source': job.get('source', 'Active Jobs DB'),
                'title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'description': job['description'],
                'url': job['url'],
                'posted_date': job.get('posted_date'),
                'salary': job.get('salary'),
                'match_score': None,  # Will be analyzed later
                'match_reasoning': None,
                'key_alignments': [],
                'potential_gaps': [],
                'priority': 'medium'
            }
            
            result = job_db.add_job(job_data)
            if result:
                stored_count += 1
                if i % 50 == 0:
                    print(f"  Stored {i}/{len(new_jobs)} jobs...")
        except Exception as e:
            print(f"  ⚠️  Error storing job {i}: {e}")
    
    print(f"✅ Successfully stored {stored_count} jobs")
    print()
    print("="*70)
    print("✅ COMPLETE!")
    print("="*70)
    print(f"Fetched: {len(all_jobs)} jobs")
    print(f"Unique: {len(unique_jobs)} jobs")
    print(f"New: {len(new_jobs)} jobs")
    print(f"Stored: {stored_count} jobs")
    print()
    
    return unique_jobs


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Bulk fetch jobs from Active Jobs DB (reads config.yaml by default)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode (no storage) with config values
  python scripts/bulk_fetch_jobs.py
  
  # Production mode with config values
  python scripts/bulk_fetch_jobs.py --production
  
  # Override config with custom values
  python scripts/bulk_fetch_jobs.py --max-jobs 500 --locations Berlin Munich --production
  
  # Fetch only remote jobs
  python scripts/bulk_fetch_jobs.py --locations "" --remote-only --production
        """
    )
    parser.add_argument('--max-jobs', type=int, default=None,
                        help='Maximum number of jobs to fetch (overrides config.yaml)')
    parser.add_argument('--date-posted', choices=['24h', 'week'], default=None,
                        help='Fetch jobs from last 24h or week (overrides config.yaml)')
    parser.add_argument('--locations', nargs='*', default=None,
                        help='Locations to search (overrides config.yaml). Example: --locations Berlin Munich Hamburg')
    parser.add_argument('--remote-only', action='store_true',
                        help='Only fetch remote jobs (overrides config.yaml)')
    parser.add_argument('--production', action='store_true',
                        help='Actually store jobs in database (default is test mode)')
    
    args = parser.parse_args()
    
    test_mode = not args.production
    
    # Handle remote-only flag
    locations = args.locations
    include_remote = None
    if args.remote_only:
        locations = []  # No location-based searches
        include_remote = True
    
    fetch_and_store_jobs(
        max_jobs=args.max_jobs,
        date_posted=args.date_posted,
        locations=locations,
        include_remote=include_remote,
        test_mode=test_mode
    )
