#!/usr/bin/env python3
"""
Daily Job Cron Service

Runs daily at 6 AM CEST to load jobs posted in the last 24 hours
for all unique user query combinations.

Usage:
    # Run once (for testing)
    python scripts/daily_job_cron.py --run-once

    # Run as cron service (continuous)
    python scripts/daily_job_cron.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.user_query_loader import UserQueryLoader
from src.database.factory import get_database

load_dotenv()


def run_daily_job():
    """
    Execute daily job loading

    Loads jobs posted in the last 24 hours for all unique user query combinations
    """
    print("\n" + "=" * 80)
    print(f"DAILY JOB STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 80)

    try:
        # Get API keys
        activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')
        jsearch_key = os.getenv('JSEARCH_API_KEY')

        if not activejobs_key:
            print("❌ ERROR: ACTIVEJOBS_API_KEY not set in environment")
            return False

        if not jsearch_key:
            print("⚠️  WARNING: JSEARCH_API_KEY not set - will only use Active Jobs DB")

        # Initialize database
        db = get_database()

        # Create loader with both API keys
        loader = UserQueryLoader(activejobs_key, db, jsearch_key)

        # Load jobs from last 24 hours
        print("\n📥 Loading jobs from last 24 hours...")
        stats = loader.load_jobs_for_all_users(date_posted='24h')

        # Check for errors
        if stats.get('error') or stats.get('cancelled'):
            print(f"\n❌ Daily job failed!")
            return False

        # Print success summary
        print(f"\n✅ Daily job completed successfully!")
        print(f"   • Unique combinations: {stats['total_queries']}")
        print(f"   • Jobs fetched: {stats['quota_used']}")
        print(f"   • New jobs added: {stats['new_jobs_added']}")
        print(f"   • Duplicates skipped: {stats['duplicates_skipped']}")

        if stats.get('query_deduplication_savings', 0) > 0:
            print(f"   • Quota saved by deduplication: {stats['query_deduplication_savings']} calls")

        db.close()
        return True

    except Exception as e:
        print(f"\n❌ ERROR during daily job: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n" + "=" * 80)
        print(f"DAILY JOB FINISHED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("=" * 80 + "\n")


def main():
    """Main entry point for cron service"""
    import argparse

    parser = argparse.ArgumentParser(description='Daily job cron service')
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run once and exit (for testing)'
    )
    parser.add_argument(
        '--schedule',
        default='6:00',
        help='Daily run time in HH:MM format (default: 6:00)'
    )
    args = parser.parse_args()

    if args.run_once:
        # Run once and exit
        print("Running in TEST MODE (run once and exit)")
        success = run_daily_job()
        sys.exit(0 if success else 1)

    # Run as scheduled cron service
    print("=" * 80)
    print("DAILY JOB CRON SERVICE")
    print("=" * 80)
    print(f"Schedule: Every day at {args.schedule} CEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("\nPress Ctrl+C to stop the service\n")

    # Parse schedule time
    hour, minute = map(int, args.schedule.split(':'))

    # Create scheduler with CEST timezone
    cest = pytz.timezone('Europe/Berlin')
    scheduler = BlockingScheduler(timezone=cest)

    # Schedule daily job
    trigger = CronTrigger(
        hour=hour,
        minute=minute,
        timezone=cest
    )

    scheduler.add_job(
        run_daily_job,
        trigger=trigger,
        id='daily_job',
        name='Daily Job Loader',
        misfire_grace_time=3600  # Allow up to 1 hour delay
    )

    print(f"✓ Scheduled daily job at {args.schedule} CEST")
    print(f"  Next run: {scheduler.get_jobs()[0].next_run_time}")
    print()

    try:
        # Start scheduler (blocking)
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\nShutting down scheduler...")
        scheduler.shutdown()
        print("✓ Scheduler stopped gracefully")


if __name__ == "__main__":
    main()
