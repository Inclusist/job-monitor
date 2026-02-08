#!/usr/bin/env python3
"""
Daily Job Loader - Configuration-driven job collection

Reads loading strategy from config.yaml and efficiently fetches jobs:
1. All jobs in key cities (Berlin, Hamburg, etc.)
2. Flexible work arrangements (Hybrid/Remote) across Germany
3. Deduplicates and stores in database

Add new cities to config.yaml as your user base grows!
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Set
from dotenv import load_dotenv
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.activejobs import ActiveJobsCollector
from src.database.factory import get_database

load_dotenv()


class DailyJobLoader:
    """Manages daily job loading with configuration-driven strategy"""

    def __init__(self, api_key: str, db, config: dict):
        """
        Initialize loader

        Args:
            api_key: Active Jobs DB API key
            db: Database instance
            config: Configuration dictionary from config.yaml
        """
        self.collector = ActiveJobsCollector(
            api_key=api_key,
            enable_filtering=True,
            min_quality=2
        )
        self.db = db
        self.config = config
        self.stats = {
            'total_fetched': 0,
            'duplicates_skipped': 0,
            'deleted_skipped': 0,
            'new_jobs_added': 0,
            'quota_used': 0,
            'by_category': {}
        }

    def load_daily_jobs(self, use_backfill: bool = False) -> Dict:
        """
        Load jobs using strategy from config.yaml

        Args:
            use_backfill: If True, use backfill config instead of daily_loading

        Returns:
            Statistics dictionary
        """
        # Choose configuration section
        if use_backfill:
            if not self.config.get('backfill', {}).get('enabled'):
                print("❌ ERROR: Backfill is disabled in config.yaml")
                print("To enable backfill, set backfill.enabled: true in config.yaml")
                print("\n⚠️  WARNING: Backfill consumes your monthly job quota!")
                print("Review the quota calculation in config.yaml before enabling.")
                return {'error': 'Backfill disabled'}

            config_section = self.config['backfill']
            mode = "BACKFILL"

            # Show backfill warning
            print("\n" + "⚠️ " * 20)
            print("BACKFILL MODE - QUOTA WARNING")
            print("⚠️ " * 20)
            print("\n🚨 Backfilling WILL consume your monthly job quota!")
            print("   This run could use 10,000-20,000 jobs of your quota.")
            print("   See quota calculation in config.yaml for details.")
            print("\n⏰ You have 10 seconds to cancel (Ctrl+C)...")
            print("⚠️ " * 20 + "\n")

            import time
            try:
                for i in range(10, 0, -1):
                    print(f"   Starting in {i}...", end='\r')
                    time.sleep(1)
                print("\n✓ Proceeding with backfill...\n")
            except KeyboardInterrupt:
                print("\n\n❌ Backfill cancelled by user")
                return {'cancelled': True}

        else:
            config_section = self.config['daily_loading']
            mode = "DAILY"

        # Extract configuration
        key_cities = config_section.get('key_cities', [])
        flexible_work = config_section.get('flexible_work', {})
        country = flexible_work.get('country', 'Germany')
        work_arrangements = flexible_work.get('work_arrangements', [])
        max_pages = config_section.get('max_pages_per_query', 10)
        date_posted = config_section.get('date_posted', '24h')

        print("=" * 70)
        print(f"{mode} JOB LOADER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print(f"Configuration: {len(key_cities)} cities, {len(work_arrangements)} work types")
        print(f"Date filter: {date_posted}, Max pages per query: {max_pages}")

        all_jobs = []
        seen_job_ids = set()

        # Get already deleted job IDs to avoid re-adding
        deleted_ids = self.db.get_deleted_job_ids()
        print(f"Skipping {len(deleted_ids)} previously deleted jobs")

        # Strategy 1: Fetch all jobs in key cities
        if key_cities:
            print(f"\n{'='*70}")
            print("STRATEGY 1: Key Cities (All Work Arrangements)")
            print(f"{'='*70}")

            for city in key_cities:
                print(f"\nFetching jobs in {city}...")
                jobs = self._fetch_city_jobs(city, max_pages, date_posted)

                new_jobs = self._deduplicate_jobs(jobs, seen_job_ids, deleted_ids)
                all_jobs.extend(new_jobs)

                self.stats['by_category'][f'{city} (all)'] = len(new_jobs)
                print(f"  ✓ {len(jobs)} fetched, {len(new_jobs)} new/unique")

        # Strategy 2: Fetch flexible work arrangements across country
        if work_arrangements:
            print(f"\n{'='*70}")
            print(f"STRATEGY 2: {country} - Flexible Work Arrangements")
            print(f"{'='*70}")

            for work_type in work_arrangements:
                print(f"\nFetching '{work_type}' jobs in {country}...")
                jobs = self._fetch_flexible_work_jobs(
                    country, work_type, max_pages, date_posted
                )

                new_jobs = self._deduplicate_jobs(jobs, seen_job_ids, deleted_ids)
                all_jobs.extend(new_jobs)

                self.stats['by_category'][f'{country} ({work_type})'] = len(new_jobs)
                print(f"  ✓ {len(jobs)} fetched, {len(new_jobs)} new/unique")

        # Store in database
        print(f"\n{'='*70}")
        print("STORING JOBS IN DATABASE")
        print(f"{'='*70}")

        stored_count = self._store_jobs(all_jobs)

        # Update statistics
        self.stats['total_fetched'] = self.stats['quota_used']
        self.stats['new_jobs_added'] = stored_count

        # Print summary
        self._print_summary(mode)

        return self.stats

    def _fetch_city_jobs(
        self,
        city: str,
        max_pages: int,
        date_posted: str
    ) -> List[Dict]:
        """Fetch all jobs in a specific city (any work arrangement)"""
        jobs = self.collector.search_all_recent_jobs(
            location=city,
            max_pages=max_pages,
            date_posted=date_posted
            # No work arrangement filter - get ALL jobs in this city
        )

        self.stats['quota_used'] += len(jobs)
        return jobs

    def _fetch_flexible_work_jobs(
        self,
        country: str,
        work_arrangement: str,
        max_pages: int,
        date_posted: str
    ) -> List[Dict]:
        """Fetch jobs with specific work arrangement across country"""
        jobs = self.collector.search_all_recent_jobs(
            location=country,
            max_pages=max_pages,
            date_posted=date_posted,
            ai_work_arrangement=work_arrangement
        )

        self.stats['quota_used'] += len(jobs)
        return jobs

    def _deduplicate_jobs(
        self,
        jobs: List[Dict],
        seen_job_ids: Set[str],
        deleted_ids: Set[str]
    ) -> List[Dict]:
        """
        Remove duplicate and deleted jobs

        Args:
            jobs: List of job dictionaries
            seen_job_ids: Set of job IDs already seen in this run
            deleted_ids: Set of job IDs previously deleted

        Returns:
            List of unique, non-deleted jobs
        """
        unique_jobs = []

        for job in jobs:
            job_id = job.get('external_id') or job.get('url', '')

            # Skip if already seen in this run
            if job_id in seen_job_ids:
                self.stats['duplicates_skipped'] += 1
                continue

            # Skip if previously deleted
            if job_id in deleted_ids:
                self.stats['deleted_skipped'] += 1
                continue

            # Add to results
            seen_job_ids.add(job_id)
            unique_jobs.append(job)

        return unique_jobs

    def _store_jobs(self, jobs: List[Dict]) -> int:
        """
        Store jobs in database

        Args:
            jobs: List of job dictionaries

        Returns:
            Number of jobs successfully stored
        """
        stored_count = 0

        for i, job in enumerate(jobs, 1):
            try:
                # Create unique job_id
                job_id = job.get('external_id') or f"{job['company']}_{job['title']}_{job['location']}"
                job['job_id'] = job_id

                # Add to database
                result = self.db.add_job(job)

                if result:
                    stored_count += 1
                    if stored_count % 50 == 0:
                        print(f"  Stored {stored_count}/{len(jobs)} jobs...")

            except Exception as e:
                print(f"  Warning: Could not store job {i}: {e}")
                continue

        print(f"  ✓ Successfully stored {stored_count}/{len(jobs)} jobs")
        return stored_count

    def _print_summary(self, mode: str):
        """Print loading summary"""
        print(f"\n{'='*70}")
        print(f"{mode} LOADING SUMMARY")
        print(f"{'='*70}")

        print(f"\nQuota Usage:")
        print(f"  Jobs fetched from API: {self.stats['quota_used']}")
        print(f"  Duplicates skipped: {self.stats['duplicates_skipped']}")
        print(f"  Previously deleted skipped: {self.stats['deleted_skipped']}")
        print(f"  New jobs added to DB: {self.stats['new_jobs_added']}")

        print(f"\nBreakdown by Category:")
        for category, count in sorted(self.stats['by_category'].items()):
            print(f"  {category}: {count}")

        # Quota analysis
        ultra_plan_quota = 20000
        quota_percent = (self.stats['quota_used'] / ultra_plan_quota) * 100

        print(f"\nQuota Analysis (Ultra Plan: {ultra_plan_quota:,} jobs/month):")
        print(f"  This run used: {self.stats['quota_used']:,} jobs ({quota_percent:.1f}% of monthly quota)")

        if mode == "BACKFILL":
            remaining = ultra_plan_quota - self.stats['quota_used']
            print(f"  Remaining quota: {remaining:,} jobs")
            if remaining < 5000:
                print(f"  ⚠️  WARNING: Less than 5,000 jobs remaining for daily updates!")
            else:
                print(f"  ✓ Good! {remaining:,} jobs left for daily updates this month")

        elif mode == "DAILY":
            estimated_monthly = self.stats['quota_used'] * 30
            print(f"  Projected monthly: {self.stats['quota_used']:,}/day × 30 = {estimated_monthly:,} jobs/month")

            if estimated_monthly > ultra_plan_quota:
                overage_percent = ((estimated_monthly / ultra_plan_quota) - 1) * 100
                print(f"  ⚠️  WARNING: Projected {overage_percent:.0f}% OVER quota!")
                print(f"  💡 Reduce max_pages_per_query in config.yaml")
            else:
                utilization = (estimated_monthly / ultra_plan_quota) * 100
                print(f"  ✓ Good! Projected {utilization:.0f}% quota utilization")

        print(f"\n{'='*70}")


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def main():
    """Run daily job loader"""
    import argparse

    parser = argparse.ArgumentParser(description='Load jobs using config-driven strategy')
    parser.add_argument('--backfill', action='store_true',
                       help='Use backfill configuration instead of daily')
    parser.add_argument('--dry-run', action='store_true',
                       help='Fetch jobs but do not store in database')
    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Get API key
    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    if not api_key:
        print("Error: ACTIVEJOBS_API_KEY not set in .env")
        return

    # Initialize database
    db = get_database()

    # Create loader
    loader = DailyJobLoader(api_key, db, config)

    # Run load
    try:
        stats = loader.load_daily_jobs(use_backfill=args.backfill)

        print(f"\n✅ Job loading completed successfully!")

        # Show how to add new cities
        if not args.backfill:
            print("\n💡 TIP: To add new cities (e.g., when user from Frankfurt joins):")
            print("   1. Open config.yaml")
            print("   2. Add 'Frankfurt' to daily_loading.key_cities")
            print("   3. Run this script again")

    except Exception as e:
        print(f"\n❌ Error during job loading: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
