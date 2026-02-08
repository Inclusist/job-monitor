#!/usr/bin/env python3
"""
User-Specific Backfill - Load 1 month of jobs for a single user

Triggered when:
1. New user signs up and uploads CV
2. User updates their search parameters

Uses both JSearch and Active Jobs DB with 1-month date filter
"""

import os
from typing import Dict, List
from datetime import datetime

from src.collectors.jsearch import JSearchCollector
from src.collectors.activejobs_backfill import ActiveJobsBackfillCollector


class UserBackfillService:
    """Backfill jobs for a specific user"""

    def __init__(self, jsearch_key: str = None, activejobs_key: str = None, db=None):
        """
        Initialize backfill service

        Args:
            jsearch_key: JSearch API key
            activejobs_key: Active Jobs DB API key
            db: Database instance
        """
        self.jsearch_collector = JSearchCollector(jsearch_key) if jsearch_key else None
        self.activejobs_collector = ActiveJobsBackfillCollector(activejobs_key) if activejobs_key else None
        self.db = db

        self.stats = {
            'user_email': None,
            'jsearch_jobs': 0,
            'activejobs_jobs': 0,
            'total_fetched': 0,
            'duplicates_skipped': 0,
            'new_jobs_added': 0,
            'quota_used': {
                'jsearch': 0,
                'activejobs': 0
            }
        }

    def backfill_user(
        self,
        user_id: int,
        user_email: str,
        use_jsearch: bool = True,
        use_activejobs: bool = True
    ) -> Dict:
        """
        Backfill 1 month of jobs for a specific user

        Args:
            user_id: User ID
            user_email: User email (for logging)
            use_jsearch: Whether to use JSearch
            use_activejobs: Whether to use Active Jobs DB

        Returns:
            Statistics dictionary
        """
        print("=" * 70)
        print(f"USER BACKFILL - {user_email}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        self.stats['user_email'] = user_email

        # Get ONLY combinations that haven't been backfilled yet
        unbacked_combinations = self.db.get_unbacked_combinations_for_user(user_id)

        if not unbacked_combinations:
            print(f"\n✅ All combinations for user {user_email} already backfilled!")
            print("No new backfill needed - user can access existing jobs")
            return {
                'user_email': user_email,
                'already_backfilled': True,
                'new_combinations': 0
            }

        print(f"\n📊 Backfill Analysis:")
        print(f"  New combinations to backfill: {len(unbacked_combinations)}")
        print(f"  (Other combinations already backfilled by other users)")

        for combo in unbacked_combinations[:5]:  # Show first 5
            print(f"    - {combo.get('title_keyword')} in {combo.get('location')}")
        if len(unbacked_combinations) > 5:
            print(f"    ... and {len(unbacked_combinations) - 5} more")

        # Get deleted job IDs to skip
        deleted_ids = self.db.get_deleted_job_ids()

        all_jobs = []
        seen_job_ids = set()

        # Fetch from JSearch (if enabled)
        if use_jsearch and self.jsearch_collector:
            print(f"\n{'='*70}")
            print("JSEARCH - 1 MONTH BACKFILL")
            print(f"{'='*70}")

            jsearch_jobs = self._backfill_jsearch(unbacked_combinations)
            jsearch_unique = self._deduplicate_jobs(jsearch_jobs, seen_job_ids, deleted_ids)
            all_jobs.extend(jsearch_unique)

            self.stats['jsearch_jobs'] = len(jsearch_unique)
            self.stats['quota_used']['jsearch'] = len(jsearch_jobs)

            print(f"\n✓ JSearch: {len(jsearch_jobs)} fetched, {len(jsearch_unique)} unique")

        # Fetch from Active Jobs DB (if enabled)
        if use_activejobs and self.activejobs_collector:
            print(f"\n{'='*70}")
            print("ACTIVE JOBS DB - 1 MONTH BACKFILL")
            print(f"{'='*70}")

            activejobs_jobs = self._backfill_activejobs(unbacked_combinations)
            activejobs_unique = self._deduplicate_jobs(activejobs_jobs, seen_job_ids, deleted_ids)
            all_jobs.extend(activejobs_unique)

            self.stats['activejobs_jobs'] = len(activejobs_unique)
            self.stats['quota_used']['activejobs'] = len(activejobs_jobs)

            print(f"\n✓ Active Jobs DB: {len(activejobs_jobs)} fetched, {len(activejobs_unique)} unique")

        # Mark all combinations as backfilled
        print(f"\n📝 Marking {len(unbacked_combinations)} combinations as backfilled...")
        for combo in unbacked_combinations:
            self.db.mark_combination_backfilled(
                title_keyword=combo.get('title_keyword'),
                location=combo.get('location'),
                ai_work_arrangement=combo.get('ai_work_arrangement'),
                ai_employment_type=combo.get('ai_employment_type'),
                ai_seniority=combo.get('ai_seniority'),
                ai_industry=combo.get('ai_industry'),
                jobs_found=len(all_jobs)  # Approximate
            )

        # Store jobs
        print(f"\n{'='*70}")
        print("STORING JOBS")
        print(f"{'='*70}")

        stored_count = self._store_jobs(all_jobs)
        self.stats['total_fetched'] = len(all_jobs)
        self.stats['new_jobs_added'] = stored_count

        # Print summary
        self._print_summary()

        return self.stats

    def _backfill_jsearch(self, queries: List[Dict]) -> List[Dict]:
        """
        Backfill from JSearch with 1-month filter

        Handles two types of searches:
        1. Location-specific: "Data Scientist in Berlin"
        2. Remote-only: "Data Scientist" with remote_jobs_only=true

        Args:
            queries: User's normalized query rows

        Returns:
            List of jobs
        """
        all_jobs = []

        # Group by unique (title, location) combinations
        combinations = set()

        for query in queries:
            title = query.get('title_keyword')
            location = query.get('location')

            if not title:
                continue

            # Check if this is a remote search
            is_remote = location and location.lower() == 'remote'

            # Add combination: (title, location or None if remote, is_remote flag)
            if is_remote:
                combinations.add((title, None, True))  # Remote search, no location
            else:
                combinations.add((title, location, False))  # Regular location search

        print(f"\nSearching {len(combinations)} title+location combinations in JSearch...")

        for title, location, is_remote in combinations:
            # Build display string
            if is_remote:
                display = f"{title} (remote only)"
            elif location:
                display = f"{title} in {location}"
            else:
                display = title

            print(f"\n  Searching: {display}")

            # JSearch: date_posted="month" for 1-month backfill
            jobs = self.jsearch_collector.search_jobs(
                query=title,  # Just title, location added by collector
                location=location,  # Collector adds "in {location}" if provided
                num_pages=10,  # API stops when no more results
                date_posted="month",
                country="de",
                remote_jobs_only=is_remote
            )

            all_jobs.extend(jobs)
            print(f"    Found {len(jobs)} jobs")

        return all_jobs

    def _backfill_activejobs(self, queries: List[Dict]) -> List[Dict]:
        """
        Backfill from Active Jobs DB using TWO search strategies:

        1. City-specific searches: Search in specific cities (Berlin, Hamburg) for ALL jobs
        2. Germany-wide remote/hybrid: Search all Germany for remote/hybrid jobs only

        Uses pipe operators for efficiency.
        Example: "Data Scientist|ML Engineer" in "Berlin" (1 API call instead of 2)

        Args:
            queries: User's normalized query rows

        Returns:
            List of jobs
        """
        all_jobs = []

        # Collect all unique titles
        all_titles = set()
        specific_locations = set()

        for query in queries:
            title = query.get('title_keyword')
            if title:
                all_titles.add(title)

            location = query.get('location', 'Germany')
            # Collect specific city locations (not "Germany" or "Remote")
            if location and location not in ['Germany', 'Remote'] and location.lower() != 'remote':
                specific_locations.add(location)

        # Format titles for advanced_title_filter: 'title1' | 'title2' | 'title3'
        piped_titles = ' | '.join(f"'{title}'" for title in sorted(all_titles)) if all_titles else None

        if not piped_titles:
            print("\n⚠️  No titles found in queries, skipping Active Jobs DB backfill")
            return []

        print(f"\nActive Jobs DB Backfill Strategy:")
        print(f"  Titles: {piped_titles}")
        print(f"  Specific locations: {', '.join(sorted(specific_locations)) if specific_locations else 'None'}")

        # STRATEGY 1: City-specific searches (ALL jobs, no work arrangement filter)
        if specific_locations:
            print(f"\n📍 STRATEGY 1: Searching {len(specific_locations)} specific locations for ALL jobs...")

            for location in sorted(specific_locations):
                # Try to clean location - Active Jobs DB might not like "Berlin, Germany" format
                # Try just the city name "Berlin" instead
                clean_location = location.split(',')[0].strip() if ',' in location else location

                print(f"\n  Location: {location} (searching as: {clean_location})")

                jobs = self.activejobs_collector.search_backfill(
                    query=piped_titles,
                    location=clean_location,
                    limit=500
                )

                all_jobs.extend(jobs)
                print(f"    ✓ Found {len(jobs)} jobs")

        # STRATEGY 2: Germany-wide search for remote/hybrid jobs ONLY
        print(f"\n🌍 STRATEGY 2: Searching Germany for remote/hybrid jobs...")

        # Search with work arrangement filter for remote/hybrid
        remote_work_types = "Hybrid,Remote OK,Remote Solely"
        print(f"  Location: Germany")
        print(f"  Work arrangements: {remote_work_types}")

        jobs = self.activejobs_collector.search_backfill(
            query=piped_titles,
            location="Germany",
            limit=500,
            ai_work_arrangement=remote_work_types
        )

        all_jobs.extend(jobs)
        print(f"    ✓ Found {len(jobs)} jobs")

        print(f"\n📊 Total jobs from Active Jobs DB: {len(all_jobs)}")
        return all_jobs

    def _get_unique_combinations(self, queries: List[Dict]) -> List[Dict]:
        """Get unique combinations from user's queries"""
        seen = set()
        unique = []

        for query in queries:
            key = (
                query.get('title_keyword'),
                query.get('location'),
                query.get('ai_work_arrangement'),
                query.get('ai_seniority')
            )

            if key not in seen:
                seen.add(key)
                unique.append(query)

        return unique

    @staticmethod
    def normalize_location(location: str) -> str:
        """
        Normalize location string for deduplication

        Removes country suffixes to treat "Berlin" and "Berlin, Germany" as same location.
        This helps deduplicate jobs from different sources that use different location formats.

        Args:
            location: Location string from job posting

        Returns:
            Normalized location (lowercase, no country suffix)

        Examples:
            >>> normalize_location("Berlin, Germany")
            'berlin'
            >>> normalize_location("Munich, DE")
            'munich'
            >>> normalize_location("Hamburg")
            'hamburg'
        """
        if not location:
            return ''

        location = location.strip()

        # Remove common country suffixes for Germany
        country_suffixes = [', Germany', ', DE', ', Deutschland']
        for suffix in country_suffixes:
            if location.endswith(suffix):
                location = location[:-len(suffix)].strip()

        return location.lower()

    def _deduplicate_jobs(
        self,
        jobs: List[Dict],
        seen_job_ids: set,
        deleted_ids: set
    ) -> List[Dict]:
        """
        Remove duplicate and deleted jobs using both ID and content-based deduplication

        Uses two deduplication strategies:
        1. Primary: external_id or URL (catches same job from same source)
        2. Secondary: (title, company, normalized_location) signature (catches same job from different sources)

        This prevents jobs like "Berlin" and "Berlin, Germany" from being stored as duplicates.

        Args:
            jobs: List of job dictionaries to deduplicate
            seen_job_ids: Set of external_ids/URLs already seen
            deleted_ids: Set of job_ids that have been deleted/hidden

        Returns:
            List of unique jobs
        """
        unique_jobs = []
        seen_signatures = set()  # Track content-based signatures

        for job in jobs:
            # Primary deduplication key: external_id or URL
            job_id = job.get('external_id') or job.get('url', '') or job.get('job_id', '')

            # Secondary deduplication: content-based signature
            signature = (
                job.get('title', '').lower().strip(),
                job.get('company', '').lower().strip(),
                self.normalize_location(job.get('location', ''))
            )

            # Check primary key (external_id)
            if job_id and job_id in seen_job_ids:
                self.stats['duplicates_skipped'] += 1
                continue

            # Check secondary key (content signature) - catches cross-source duplicates
            if signature in seen_signatures:
                self.stats['duplicates_skipped'] += 1
                continue

            # Check deleted jobs
            if job_id and job_id in deleted_ids:
                continue

            # Add to both tracking sets
            if job_id:
                seen_job_ids.add(job_id)
            seen_signatures.add(signature)

            unique_jobs.append(job)

        return unique_jobs

    def _store_jobs(self, jobs: List[Dict]) -> int:
        """Store jobs in database"""
        stored_count = 0

        for i, job in enumerate(jobs, 1):
            try:
                job_id = job.get('external_id') or job.get('job_id') or f"{job['company']}_{job['title']}"
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
        """Print backfill summary"""
        print(f"\n{'='*70}")
        print(f"BACKFILL SUMMARY - {self.stats['user_email']}")
        print(f"{'='*70}")

        print(f"\nJobs Fetched:")
        print(f"  JSearch: {self.stats['jsearch_jobs']}")
        print(f"  Active Jobs DB: {self.stats['activejobs_jobs']}")
        print(f"  Total: {self.stats['total_fetched']}")

        print(f"\nQuota Used:")
        print(f"  JSearch: {self.stats['quota_used']['jsearch']} jobs")
        print(f"  Active Jobs DB: {self.stats['quota_used']['activejobs']} jobs")

        print(f"\nResults:")
        print(f"  Duplicates skipped: {self.stats['duplicates_skipped']}")
        print(f"  New jobs added: {self.stats['new_jobs_added']}")

        print(f"\n✅ User {self.stats['user_email']} backfill completed!")
        print(f"{'='*70}")


def backfill_user_on_signup(user_id: int, user_email: str, db) -> Dict:
    """
    Convenience function to backfill jobs for a new user

    Call this after user uploads CV and queries are auto-generated

    Args:
        user_id: User ID
        user_email: User email
        db: Database instance

    Returns:
        Backfill statistics
    """
    jsearch_key = os.getenv('JSEARCH_API_KEY')
    activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')

    # Warn if API keys are missing
    if not jsearch_key:
        print("⚠️  WARNING: JSEARCH_API_KEY not set - skipping JSearch backfill")
    if not activejobs_key:
        print("⚠️  WARNING: ACTIVEJOBS_API_KEY not set - skipping ActiveJobs backfill")

    if not jsearch_key and not activejobs_key:
        print("❌ ERROR: No API keys configured - cannot run backfill!")
        return {
            'user_email': user_email,
            'error': 'No API keys configured',
            'new_jobs_added': 0
        }

    service = UserBackfillService(
        jsearch_key=jsearch_key,
        activejobs_key=activejobs_key,
        db=db
    )

    return service.backfill_user(
        user_id=user_id,
        user_email=user_email,
        use_jsearch=bool(jsearch_key),
        use_activejobs=bool(activejobs_key)
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    from src.database.factory import get_database

    load_dotenv()

    # Test backfill for user 1
    db = get_database()

    stats = backfill_user_on_signup(
        user_id=1,
        user_email="test@example.com",
        db=db
    )

    print(f"\nBackfill completed: {stats}")
