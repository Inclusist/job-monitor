#!/usr/bin/env python3
"""
User Query-Based Job Loader

Fetches jobs based on personalized search queries stored in user_search_queries table.
Uses Active Jobs DB's pipe operator (|) for efficient OR queries.

This is the RECOMMENDED approach for job loading - quota-efficient and personalized!
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Set
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.activejobs import ActiveJobsCollector
from src.database.factory import get_database

load_dotenv()


class UserQueryLoader:
    """Loads jobs based on user-defined search queries"""

    def __init__(self, api_key: str, db):
        """
        Initialize loader

        Args:
            api_key: Active Jobs DB API key
            db: Database instance (with CV manager methods)
        """
        self.collector = ActiveJobsCollector(
            api_key=api_key,
            enable_filtering=True,
            min_quality=2
        )
        self.db = db
        self.stats = {
            'total_queries': 0,
            'total_fetched': 0,
            'duplicates_skipped': 0,
            'deleted_skipped': 0,
            'new_jobs_added': 0,
            'quota_used': 0,
            'by_query': {},
            'query_deduplication_savings': 0
        }

    def load_jobs_for_all_users(self, date_posted: str = '24h') -> Dict:
        """
        Load jobs for all users based on their search queries

        Args:
            date_posted: Time filter ('24h' or 'week')

        Returns:
            Statistics dictionary
        """
        print("=" * 70)
        print(f"USER QUERY LOADER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Get all active queries (for stats)
        all_queries = self.db.get_all_active_queries()

        # Get UNIQUE query combinations (for execution)
        unique_combinations = self.db.get_unique_query_combinations()

        if not unique_combinations:
            print("\n⚠️  No active search queries found!")
            print("Users need to upload CVs or manually create search queries.")
            return self.stats

        print(f"\n📊 Query Analysis:")
        print(f"  Total query rows: {len(all_queries)}")
        print(f"  Unique combinations: {len(unique_combinations)}")

        if len(all_queries) > len(unique_combinations):
            saved = len(all_queries) - len(unique_combinations)
            savings_pct = (saved / len(all_queries)) * 100
            print(f"  ✅ Quota saved: {saved} API calls ({savings_pct:.1f}%)")
            self.stats['query_deduplication_savings'] = saved
        else:
            print(f"  No duplicate queries found")
            self.stats['query_deduplication_savings'] = 0

        # Get deleted job IDs to skip
        deleted_ids = self.db.get_deleted_job_ids()
        print(f"Skipping {len(deleted_ids)} previously deleted jobs\n")

        all_jobs = []
        seen_job_ids = set()

        # Process each UNIQUE combination (deduplicated!)
        for i, combination in enumerate(unique_combinations, 1):
            print(f"\n{'='*70}")
            print(f"Combination {i}/{len(unique_combinations)}")
            print(f"{'='*70}")

            # Execute query for this unique combination
            jobs = self._execute_combination(combination, date_posted)

            # Deduplicate
            new_jobs = self._deduplicate_jobs(jobs, seen_job_ids, deleted_ids)
            all_jobs.extend(new_jobs)

            # Update stats
            combo_key = f"{combination.get('title_keyword')} in {combination.get('location')}"
            self.stats['by_query'][combo_key] = len(new_jobs)
            self.stats['total_queries'] += 1

            print(f"✓ {len(jobs)} fetched, {len(new_jobs)} new/unique")

        # Store jobs
        print(f"\n{'='*70}")
        print("STORING JOBS IN DATABASE")
        print(f"{'='*70}")

        stored_count = self._store_jobs(all_jobs)

        # Update final stats
        self.stats['total_fetched'] = self.stats['quota_used']
        self.stats['new_jobs_added'] = stored_count

        # Print summary
        self._print_summary()

        return self.stats

    def _execute_combination(self, combination: Dict, date_posted: str) -> List[Dict]:
        """
        Execute a single search query combination using Active Jobs DB

        Args:
            combination: Unique combination dictionary (title_keyword, location, filters)
            date_posted: Time filter

        Returns:
            List of job dictionaries
        """
        # Extract combination parameters (all single values, not pipe-separated)
        title_keyword = combination.get('title_keyword')
        location = combination.get('location')
        work_arrangement = combination.get('ai_work_arrangement')
        employment_type = combination.get('ai_employment_type')
        seniority = combination.get('ai_seniority')
        industry = combination.get('ai_industry')

        # Print combination details
        print(f"  Title: {title_keyword or 'Any'}")
        print(f"  Location: {location or 'Any'}")
        if work_arrangement:
            print(f"  Work arrangement: {work_arrangement}")
        if seniority:
            print(f"  Seniority: {seniority}")

        # Execute search with single values
        jobs = self.collector.search_jobs(
            query=title_keyword or '',
            location=location,
            num_pages=1,  # Single page per combination
            results_per_page=100,
            date_posted=date_posted,
            ai_work_arrangement=work_arrangement,
            ai_employment_type=employment_type,
            ai_seniority=seniority,
            ai_industry=industry
        )

        self.stats['quota_used'] += len(jobs)
        return jobs

    def _deduplicate_jobs(
        self,
        jobs: List[Dict],
        seen_job_ids: Set[str],
        deleted_ids: Set[str]
    ) -> List[Dict]:
        """Remove duplicate and deleted jobs"""
        unique_jobs = []

        for job in jobs:
            job_id = job.get('external_id') or job.get('url', '')

            if job_id in seen_job_ids:
                self.stats['duplicates_skipped'] += 1
                continue

            if job_id in deleted_ids:
                self.stats['deleted_skipped'] += 1
                continue

            seen_job_ids.add(job_id)
            unique_jobs.append(job)

        return unique_jobs

    def _store_jobs(self, jobs: List[Dict]) -> int:
        """Store jobs in database"""
        stored_count = 0

        for i, job in enumerate(jobs, 1):
            try:
                job_id = job.get('external_id') or f"{job['company']}_{job['title']}_{job['location']}"
                job['job_id'] = job_id

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

    def _print_summary(self):
        """Print loading summary"""
        print(f"\n{'='*70}")
        print("LOADING SUMMARY")
        print(f"{'='*70}")

        print(f"\nQuota Usage:")
        print(f"  Jobs fetched from API: {self.stats['quota_used']}")
        if self.stats['query_deduplication_savings'] > 0:
            print(f"  Query deduplication saved: {self.stats['query_deduplication_savings']} API calls")
        print(f"  Duplicates skipped: {self.stats['duplicates_skipped']}")
        print(f"  Previously deleted skipped: {self.stats['deleted_skipped']}")
        print(f"  New jobs added to DB: {self.stats['new_jobs_added']}")

        print(f"\nUnique Combinations Executed: {self.stats['total_queries']}")

        print(f"\nJobs by Combination:")
        for combo, count in sorted(self.stats['by_query'].items())[:10]:  # Show top 10
            print(f"  {combo}: {count} jobs")

        # Quota projection
        ultra_plan_quota = 20000
        quota_percent = (self.stats['quota_used'] / ultra_plan_quota) * 100

        print(f"\nQuota Analysis (Ultra Plan: {ultra_plan_quota:,} jobs/month):")
        print(f"  This run used: {self.stats['quota_used']:,} jobs ({quota_percent:.1f}% of quota)")

        estimated_monthly = self.stats['quota_used'] * 30
        print(f"  Projected monthly: {self.stats['quota_used']:,}/day × 30 = {estimated_monthly:,} jobs/month")

        if estimated_monthly > ultra_plan_quota:
            overage_percent = ((estimated_monthly / ultra_plan_quota) - 1) * 100
            print(f"  ⚠️  WARNING: Projected {overage_percent:.0f}% OVER quota!")
            print(f"  💡 Consider: Reduce max_results for some queries")
        else:
            utilization = (estimated_monthly / ultra_plan_quota) * 100
            print(f"  ✓ Good! Projected {utilization:.0f}% quota utilization")

        print(f"\n{'='*70}")


def main():
    """Run user query loader"""
    import argparse

    parser = argparse.ArgumentParser(description='Load jobs based on user search queries')
    parser.add_argument('--date', default='24h', choices=['24h', 'week'],
                       help='Time filter for jobs (default: 24h)')
    parser.add_argument('--user', type=str,
                       help='Load jobs for specific user only (by email)')
    args = parser.parse_args()

    # Get API key
    api_key = os.getenv('ACTIVEJOBS_API_KEY')
    if not api_key:
        print("Error: ACTIVEJOBS_API_KEY not set in .env")
        return

    # Initialize database
    db = get_database()

    # Create loader
    loader = UserQueryLoader(api_key, db)

    try:
        stats = loader.load_jobs_for_all_users(date_posted=args.date)

        if stats.get('error') or stats.get('cancelled'):
            return

        print(f"\n✅ Job loading completed successfully!")

        print("\n💡 TIPS:")
        print("   • Users get personalized jobs automatically when they upload CVs")
        print("   • Queries are stored in user_search_queries table")
        print("   • To add/modify queries: Update user_search_queries table directly")
        print("   • Or use web UI to let users manage their own queries")

    except Exception as e:
        print(f"\n❌ Error during job loading: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
