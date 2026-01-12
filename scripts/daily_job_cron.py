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
from scripts.enrich_lightweight import run_lightweight_enrichment  # Lightweight enrichment only
import psycopg2
from psycopg2.extras import execute_values
import json
import time

load_dotenv()

# Lazy load sentence transformer model
_encoding_model = None

def get_encoding_model():
    """Load TechWolf JobBERT-v3 model (lazy loading)"""
    global _encoding_model
    if _encoding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("📥 Loading TechWolf/JobBERT-v3 model...")
            # Fix for PyTorch 2.9+ compatibility
            _encoding_model = SentenceTransformer('TechWolf/JobBERT-v3', device='cpu', trust_remote_code=True)
            print("✅ Model loaded")
        except Exception as e:
            print(f"❌ Failed to load encoding model: {e}")
            return None
    return _encoding_model


def encode_new_jobs(db, limit=None):
    """
    Encode titles of jobs that don't have embeddings yet

    Args:
        db: Database instance
        limit: Maximum number of jobs to encode (None = all)

    Returns:
        int: Number of jobs encoded
    """
    model = get_encoding_model()
    if model is None:
        return 0

    # Get jobs without embeddings
    conn = db._get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, title
        FROM jobs
        WHERE embedding_jobbert_title IS NULL
        ORDER BY discovered_date DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    jobs = cursor.fetchall()

    if not jobs:
        cursor.close()
        if hasattr(db, '_return_connection'):
            db._return_connection(conn)
        else:
            conn.close()
        return 0

    # Convert to list of dicts
    job_list = [{'id': row[0], 'title': row[1]} for row in jobs]

    cursor.close()
    if hasattr(db, '_return_connection'):
        db._return_connection(conn)
    else:
        conn.close()

    # Encode titles
    start_time = time.time()
    titles = [job['title'] for job in job_list]
    job_ids = [job['id'] for job in job_list]

    embeddings = model.encode(titles, show_progress_bar=False, convert_to_numpy=True)

    # Store embeddings
    conn = db._get_connection()
    cursor = conn.cursor()

    # Detect database type
    is_postgres = hasattr(db, 'connection_pool') or os.getenv('DATABASE_URL', '').startswith('postgres')

    try:
        for job_id, embedding in zip(job_ids, embeddings):
            embedding_json = json.dumps(embedding.tolist())

            if is_postgres:
                cursor.execute("""
                    UPDATE jobs
                    SET embedding_jobbert_title = %s::jsonb,
                        embedding_date = NOW()
                    WHERE id = %s
                """, (embedding_json, job_id))
            else:
                cursor.execute("""
                    UPDATE jobs
                    SET embedding_jobbert_title = ?,
                        embedding_date = ?
                    WHERE id = ?
                """, (embedding_json, datetime.now().isoformat(), job_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cursor.close()
        if hasattr(db, '_return_connection'):
            db._return_connection(conn)
        else:
            conn.close()

    encode_time = time.time() - start_time
    print(f"   ✓ Encoded {len(job_list)} jobs in {encode_time:.2f}s ({len(job_list)/encode_time:.1f} jobs/sec)")

    return len(job_list)


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

        # --- Trigger Lightweight Enrichment ---
        if stats['new_jobs'] > 0:
            print(f"\n🎯 Lightweight enrichment starting ({stats['new_jobs']} new jobs)...")
            print("   Extracts: location, work arrangement, employment type")
            print(f"   Estimated cost: ${stats['new_jobs'] * 0.0003:.2f}")
            try:
                run_lightweight_enrichment(limit=stats['new_jobs'])
                print(f"   ✓ Lightweight enrichment complete")
            except Exception as e:
                print(f"   ⚠️  Lightweight enrichment failed: {e}")
        # -----------------------------------------

        # --- Encode New Jobs with TechWolf JobBERT-v3 ---
        if stats['new_jobs'] > 0:
            print(f"\n🔤 Encoding job titles ({stats['new_jobs']} new jobs)...")
            print("   Model: TechWolf/JobBERT-v3 (1024-dim embeddings)")
            print("   Purpose: Pre-compute for 80x faster semantic search")
            try:
                encoded_count = encode_new_jobs(db, limit=stats['new_jobs'])
                if encoded_count > 0:
                    print(f"   ✓ Job title encoding complete")
                else:
                    print(f"   ℹ️  No jobs needed encoding (already encoded)")
            except Exception as e:
                print(f"   ⚠️  Job encoding failed: {e}")
                import traceback
                traceback.print_exc()
        # -------------------------------------------------

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
