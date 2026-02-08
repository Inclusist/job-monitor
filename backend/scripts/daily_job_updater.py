#!/usr/bin/env python3
"""
Smart Daily Job Updater

Automatically fetches fresh jobs based on registered users' search preferences.
This script is designed to run daily (via cron or scheduler) to:
1. Collect all users' search preferences (keywords + locations)
2. Deduplicate and combine similar searches
3. Fetch only recent jobs (last 1-2 days) from Arbeitsagentur
4. Update database with new postings
5. Avoid fetching duplicates

Usage:
    # Fetch jobs from last 24 hours (default)
    python scripts/daily_job_updater.py
    
    # Fetch jobs from last 2 days
    python scripts/daily_job_updater.py --days 2
    
    # Dry run (show what would be fetched without saving)
    python scripts/daily_job_updater.py --dry-run
    
    # Verbose output
    python scripts/daily_job_updater.py --verbose

Schedule with cron (daily at 6 AM):
    0 6 * * * cd /path/to/job-monitor && python scripts/daily_job_updater.py
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
from collections import defaultdict
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.arbeitsagentur import ArbeitsagenturCollector
from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgreSQLCVManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmartJobUpdater:
    """
    Smart daily job updater that uses user preferences to fetch relevant jobs
    """
    
    def __init__(self, db: PostgresDatabase, cv_manager: PostgreSQLCVManager, 
                 dry_run: bool = False):
        """
        Initialize updater
        
        Args:
            db: Database connection
            cv_manager: CV/user manager
            dry_run: If True, don't save jobs to database
        """
        self.db = db
        self.cv_manager = cv_manager
        self.dry_run = dry_run
        self.collector = ArbeitsagenturCollector()
        
        self.stats = {
            'users_analyzed': 0,
            'unique_searches': 0,
            'total_fetched': 0,
            'new_jobs_saved': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        self.seen_job_ids: Set[str] = set()
    
    def get_all_user_preferences(self) -> List[Dict]:
        """
        Get search preferences from all active users
        
        Returns:
            List of user preference dictionaries with keywords and locations
        """
        conn = self.cv_manager._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get all active users with their preferences
            cursor.execute("""
                SELECT id, email, preferences
                FROM users
                WHERE active = true
                ORDER BY id
            """)
            
            users_prefs = []
            for row in cursor.fetchall():
                user_id, email, preferences = row
                
                if preferences:
                    keywords = preferences.get('search_keywords', [])
                    locations = preferences.get('search_locations', [])
                    
                    # Only include users with at least one search criterion
                    if keywords or locations:
                        users_prefs.append({
                            'user_id': user_id,
                            'email': email,
                            'keywords': keywords,
                            'locations': locations
                        })
            
            return users_prefs
            
        finally:
            cursor.close()
            self.cv_manager._return_connection(conn)
    
    def aggregate_search_queries(self, users_prefs: List[Dict]) -> List[Tuple[str, str]]:
        """
        Combine and deduplicate user preferences into unique search queries
        
        Args:
            users_prefs: List of user preference dictionaries
        
        Returns:
            List of (keyword, location) tuples representing unique searches
        """
        unique_queries = set()
        
        # Strategy 1: Combine each keyword with each location
        all_keywords = set()
        all_locations = set()
        
        for prefs in users_prefs:
            all_keywords.update(prefs['keywords'])
            all_locations.update(prefs['locations'])
        
        # Create combinations
        if all_keywords and all_locations:
            for keyword in all_keywords:
                for location in all_locations:
                    unique_queries.add((keyword, location))
        
        # Also add keyword-only and location-only searches
        if all_keywords and not all_locations:
            for keyword in all_keywords:
                unique_queries.add((keyword, None))
        
        if all_locations and not all_keywords:
            for location in all_locations:
                unique_queries.add((None, location))
        
        logger.info(f"Aggregated searches: {len(all_keywords)} keywords × {len(all_locations)} locations")
        logger.info(f"Unique search queries: {len(unique_queries)}")
        
        return list(unique_queries)
    
    def fetch_jobs_for_query(self, keyword: str, location: str, 
                            days_since_posted: int = 1,
                            max_per_query: int = 100) -> List[Dict]:
        """
        Fetch jobs for a specific search query
        
        Args:
            keyword: Job search keyword (can be None)
            location: Location to search (can be None)
            days_since_posted: Fetch jobs from last N days
            max_per_query: Maximum jobs per query
        
        Returns:
            List of standardized job dictionaries
        """
        try:
            logger.info(f"Searching: keyword='{keyword}', location='{location}', days={days_since_posted}")
            
            # Fetch jobs from Arbeitsagentur
            jobs = self.collector.search_and_parse(
                keywords=keyword,
                location=location,
                days_since_posted=days_since_posted,
                max_results=max_per_query,
                work_time=None  # Get all work types
            )
            
            logger.info(f"  → Found {len(jobs)} jobs")
            return jobs
            
        except Exception as e:
            logger.error(f"Error fetching jobs for '{keyword}' in '{location}': {e}")
            self.stats['errors'] += 1
            return []
    
    def save_new_jobs(self, jobs: List[Dict]) -> int:
        """
        Save jobs to database, skipping duplicates
        
        Args:
            jobs: List of job dictionaries
        
        Returns:
            Number of new jobs saved
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would save {len(jobs)} jobs")
            return len(jobs)
        
        saved_count = 0
        
        for job in jobs:
            job_id = job.get('job_id')
            
            # Skip if already seen in this session
            if job_id in self.seen_job_ids:
                self.stats['duplicates_skipped'] += 1
                continue
            
            try:
                # Check if job exists in database
                existing = self.db.get_job_by_id(job_id)
                if existing:
                    self.stats['duplicates_skipped'] += 1
                    self.seen_job_ids.add(job_id)
                    continue
                
                # Save new job
                self.db.add_job(job)
                saved_count += 1
                self.seen_job_ids.add(job_id)
                
            except Exception as e:
                logger.error(f"Error saving job {job_id}: {e}")
                self.stats['errors'] += 1
        
        return saved_count
    
    def run_daily_update(self, days_since_posted: int = 1) -> Dict:
        """
        Run the daily job update workflow
        
        Args:
            days_since_posted: Fetch jobs from last N days (default: 1 = today only)
        
        Returns:
            Statistics dictionary
        """
        logger.info("="*80)
        logger.info("SMART DAILY JOB UPDATER - Starting")
        logger.info("="*80)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE UPDATE'}")
        logger.info(f"Fetching jobs from last {days_since_posted} day(s)")
        
        # Step 1: Get all user preferences
        logger.info("\nStep 1: Collecting user search preferences...")
        users_prefs = self.get_all_user_preferences()
        self.stats['users_analyzed'] = len(users_prefs)
        
        if not users_prefs:
            logger.warning("No users with search preferences found!")
            logger.info("Consider running with default searches or adding user preferences")
            return self.stats
        
        logger.info(f"Found {len(users_prefs)} users with search preferences")
        
        # Show user preferences summary
        for prefs in users_prefs[:5]:  # Show first 5
            logger.info(f"  - {prefs['email']}: {len(prefs['keywords'])} keywords, {len(prefs['locations'])} locations")
        if len(users_prefs) > 5:
            logger.info(f"  ... and {len(users_prefs) - 5} more users")
        
        # Step 2: Aggregate into unique search queries
        logger.info("\nStep 2: Aggregating unique search queries...")
        search_queries = self.aggregate_search_queries(users_prefs)
        self.stats['unique_searches'] = len(search_queries)
        
        if not search_queries:
            logger.warning("No valid search queries generated!")
            return self.stats
        
        # Show query summary
        logger.info(f"Generated {len(search_queries)} unique queries:")
        for query in search_queries[:10]:  # Show first 10
            keyword, location = query
            logger.info(f"  - '{keyword or 'any'}' in '{location or 'Germany'}'")
        if len(search_queries) > 10:
            logger.info(f"  ... and {len(search_queries) - 10} more queries")
        
        # Step 3: Fetch jobs for each query
        logger.info(f"\nStep 3: Fetching fresh jobs (last {days_since_posted} day(s))...")
        all_jobs = []
        
        for i, (keyword, location) in enumerate(search_queries, 1):
            logger.info(f"\n[Query {i}/{len(search_queries)}]")
            
            jobs = self.fetch_jobs_for_query(
                keyword=keyword,
                location=location,
                days_since_posted=days_since_posted,
                max_per_query=100
            )
            
            all_jobs.extend(jobs)
            self.stats['total_fetched'] += len(jobs)
            
            # Rate limiting - be nice to the API
            if i < len(search_queries):
                time.sleep(0.5)
        
        # Step 4: Save new jobs to database
        logger.info(f"\nStep 4: Saving jobs to database...")
        logger.info(f"Total jobs fetched: {len(all_jobs)}")
        
        saved_count = self.save_new_jobs(all_jobs)
        self.stats['new_jobs_saved'] = saved_count
        
        # Print summary
        self._print_summary()
        
        return self.stats
    
    def _print_summary(self):
        """Print execution summary"""
        duration = datetime.now() - self.stats['start_time']
        
        print("\n" + "="*80)
        print("DAILY JOB UPDATE SUMMARY")
        print("="*80)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE UPDATE'}")
        print(f"Duration: {duration}")
        print(f"Users analyzed: {self.stats['users_analyzed']}")
        print(f"Unique search queries: {self.stats['unique_searches']}")
        print(f"Total jobs fetched: {self.stats['total_fetched']}")
        print(f"New jobs saved: {self.stats['new_jobs_saved']}")
        print(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total_fetched'] > 0:
            success_rate = (self.stats['new_jobs_saved'] / self.stats['total_fetched']) * 100
            print(f"New job rate: {success_rate:.1f}%")
        
        print("="*80)


def run_with_default_searches(updater: SmartJobUpdater, days_since_posted: int = 1):
    """
    Fallback: Run with default searches if no user preferences exist
    
    Args:
        updater: SmartJobUpdater instance
        days_since_posted: Days to look back
    """
    logger.info("\n" + "="*80)
    logger.info("FALLBACK: Using default search parameters")
    logger.info("="*80)
    
    # Default searches for common tech jobs
    default_searches = [
        ("Software Engineer", "Berlin"),
        ("Software Engineer", "München"),
        ("Python Developer", "Berlin"),
        ("Data Scientist", "Frankfurt"),
        ("DevOps Engineer", "Hamburg"),
        ("Full Stack Developer", "Stuttgart"),
    ]
    
    all_jobs = []
    
    for keyword, location in default_searches:
        logger.info(f"Searching: '{keyword}' in '{location}'")
        jobs = updater.fetch_jobs_for_query(keyword, location, days_since_posted)
        all_jobs.extend(jobs)
        updater.stats['total_fetched'] += len(jobs)
        time.sleep(0.5)
    
    saved_count = updater.save_new_jobs(all_jobs)
    updater.stats['new_jobs_saved'] = saved_count
    updater.stats['unique_searches'] = len(default_searches)
    
    updater._print_summary()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Smart daily job updater based on user search preferences"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Fetch jobs from last N days (default: 1 = today only)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without saving to database'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--use-defaults',
        action='store_true',
        help='Use default searches instead of user preferences'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize database connections
    logger.info("Connecting to database...")
    db = PostgresDatabase()
    cv_manager = PostgreSQLCVManager(db.conn_pool)
    
    # Initialize updater
    updater = SmartJobUpdater(db, cv_manager, dry_run=args.dry_run)
    
    try:
        if args.use_defaults:
            # Use default searches
            run_with_default_searches(updater, args.days)
        else:
            # Use user preferences (smart mode)
            updater.run_daily_update(days_since_posted=args.days)
    
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        # Close database
        db.close()
    
    # Return exit code based on success
    if updater.stats['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
