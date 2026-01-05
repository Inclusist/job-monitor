#!/usr/bin/env python3
"""
Daily Job Cron Service

Runs daily to collect jobs posted in the last 24 hours from Active Jobs DB.
Uses the 24h endpoint for better quality job data.

Usage:
    # Run once (for testing)
    python scripts/daily_job_cron.py --run-once

    # Run as cron service (continuous, every 24 hours)
    python scripts/daily_job_cron.py --interval 1440

    # Run at custom interval (minutes)
    python scripts/daily_job_cron.py --interval 60
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collectors.activejobs import ActiveJobsCollector
from src.database.factory import get_database
from scripts.enrich_missing_jobs import enrich_jobs  # Import enrichment agent
import psycopg2
from psycopg2.extras import execute_values
import json

load_dotenv()


def collect_daily_jobs(db, api_key):
    """
    Collect jobs from the last 24 hours using Active Jobs DB daily endpoint

    Uses the 24h endpoint for better quality - jobs are from last 24 hours.

    Returns:
        dict: Statistics about the collection
    """
    print("\n📥 Collecting jobs from last 24 hours...")

    collector = ActiveJobsCollector(
        api_key=api_key,
        enable_filtering=False,  # No filtering - get everything
        min_quality=1
    )

    # Fetch jobs from last 24 hours (cleaner data than 1h endpoint)
    jobs = collector.search_all_recent_jobs(
        location="Germany",
        max_pages=15,  # Up to 1500 jobs per day (only charged for actual results)
        date_posted="24h",  # 24-HOUR endpoint (better quality)
        remote_only=False
    )

    if not jobs:
        print("  No new jobs in the last 24 hours")
        return {
            'new_jobs': 0,
            'duplicates': 0,
            'quota_used': 0
        }

    print(f"  ✓ Fetched {len(jobs)} jobs from API")

    # Store jobs in database
    conn = db._get_connection()
    cursor = conn.cursor()

    new_count = 0
    duplicate_count = 0

    for job in jobs:
        try:
            job_id = db.add_job(job)
            if job_id:
                new_count += 1
            else:
                duplicate_count += 1
        except Exception as e:
            print(f"  ⚠️ Error adding job: {e}")
            continue

    cursor.close()
    db._return_connection(conn)

    return {
        'new_jobs': new_count,
        'duplicates': duplicate_count,
        'quota_used': len(jobs)
    }


def run_daily_job():
    """
    Execute daily job collection

    Collects jobs posted in the last 24 hours from Active Jobs DB
    """
    print("\n" + "=" * 80)
    print(f"DAILY JOB STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 80)

    try:
        # Get API key
        activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')

        if not activejobs_key:
            print("❌ ERROR: ACTIVEJOBS_API_KEY not set in environment")
            return False

        # Initialize database
        db = get_database()

        # Collect jobs
        stats = collect_daily_jobs(db, activejobs_key)

        # Print summary
        print(f"\n✅ Job collection completed successfully!")
        print(f"   • New jobs added: {stats['new_jobs']}")
        print(f"   • Duplicates skipped: {stats['duplicates']}")
        print(f"   • API quota used: {stats['quota_used']}")

        # Get current total
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total = cursor.fetchone()[0]
        cursor.close()
        db._return_connection(conn)

        print(f"   • Total jobs in database: {total:,}")

        # --- Trigger Enrichment Agent ---
        print("\n🤖 Enrichment agent starting...")
        # We need a raw pyscopg2 connection for the agent,
        # but the db object might be a wrapper. Let's get a raw connection.
        agent_conn = db._get_connection()
        try:
            enrich_stats = enrich_jobs(agent_conn, limit=100) # Enrich 100 jobs per day
            print(f"   • Enrichment Agent: Processed {enrich_stats['processed']} (Success: {enrich_stats['success']}, Failed: {enrich_stats['failed']})")
        except Exception as e:
            print(f"   ⚠️ Enrichment Agent failed: {e}")
        finally:
            db._return_connection(agent_conn)
        # --------------------------------
        
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
    """Main entry point for daily cron service"""
    import argparse

    parser = argparse.ArgumentParser(description='Daily job cron service')
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run once and exit (for testing)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Interval in minutes (default: 60)'
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
    print(f"Interval: Every {args.interval} minutes")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("\nPress Ctrl+C to stop the service\n")

    # Create scheduler
    cest = pytz.timezone('Europe/Berlin')
    scheduler = BlockingScheduler(timezone=cest)

    # Schedule daily job
    trigger = IntervalTrigger(
        minutes=args.interval,
        timezone=cest
    )

    scheduler.add_job(
        run_daily_job,
        trigger=trigger,
        id='daily_job',
        name='Daily Job Collector',
        misfire_grace_time=600  # Allow up to 10 minutes delay
    )

    print(f"✓ Scheduled daily job (every {args.interval} minutes)")
    print(f"  Next run: {scheduler.get_jobs()[0].next_run_time}")
    print()

    # Run immediately on start
    print("▶ Running initial collection...")
    run_daily_job()

    try:
        # Start scheduler (blocking)
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\nShutting down scheduler...")
        scheduler.shutdown()
        print("✓ Scheduler stopped gracefully")


if __name__ == "__main__":
    main()
