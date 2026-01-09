#!/usr/bin/env python3
"""
Encode Existing Jobs with TechWolf JobBERT-v3

Pre-computes title embeddings for all jobs in the database for 80x faster semantic search.

Usage:
    python scripts/encode_existing_jobs.py --dry-run --limit 10  # Test with 10 jobs
    python scripts/encode_existing_jobs.py --limit 100           # Encode 100 jobs
    python scripts/encode_existing_jobs.py                       # Encode all jobs
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.factory import get_database
import argparse
import numpy as np


def load_model():
    """Load TechWolf JobBERT-v3 model"""
    try:
        from sentence_transformers import SentenceTransformer
        print("📥 Loading TechWolf/JobBERT-v3 model...")
        model = SentenceTransformer('TechWolf/JobBERT-v3')
        print("✅ Model loaded successfully")
        return model
    except ImportError:
        print("❌ Error: sentence-transformers package not installed")
        print("   Install with: pip install sentence-transformers")
        return None
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None


def get_jobs_without_embeddings(db, limit=None):
    """Get jobs that don't have embeddings yet"""
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

    # Handle both PostgreSQL and SQLite cursor types
    if hasattr(cursor, 'fetchall'):
        rows = cursor.fetchall()
        # Convert to dict if needed
        if rows and not isinstance(rows[0], dict):
            jobs = [{'id': row[0], 'title': row[1]} for row in rows]
        else:
            jobs = [dict(row) for row in rows]
    else:
        jobs = []

    cursor.close()
    if hasattr(db, '_return_connection'):
        db._return_connection(conn)
    else:
        conn.close()

    return jobs


def encode_batch(model, titles, batch_size=100):
    """Encode a batch of titles"""
    embeddings = []

    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        embeddings.extend(batch_embeddings)

    return embeddings


def store_embeddings(db, job_ids, embeddings, dry_run=False):
    """Store embeddings in database"""
    if dry_run:
        return

    conn = db._get_connection()
    cursor = conn.cursor()

    # Detect database type
    is_postgres = hasattr(db, 'connection_pool') or os.getenv('DATABASE_URL', '').startswith('postgres')

    try:
        for job_id, embedding in zip(job_ids, embeddings):
            # Convert numpy array to JSON
            embedding_json = json.dumps(embedding.tolist())

            if is_postgres:
                cursor.execute("""
                    UPDATE jobs
                    SET embedding_jobbert_title = %s::jsonb,
                        embedding_date = NOW()
                    WHERE id = %s
                """, (embedding_json, job_id))
            else:
                # SQLite
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


def run_encoding(limit=None, batch_size=100, dry_run=False):
    """Main encoding function"""

    print("\n" + "="*60)
    print("ENCODE EXISTING JOBS - TechWolf JobBERT-v3")
    print("="*60)

    if dry_run:
        print("🔍 DRY RUN MODE - No database updates")
    else:
        print("⚠️  PRODUCTION MODE - Database will be updated")

    print(f"\nConfiguration:")
    print(f"  • Batch size: {batch_size} jobs")
    print(f"  • Limit: {limit if limit else 'All jobs'}")
    print(f"  • Model: TechWolf/JobBERT-v3 (768 dimensions)")
    print(f"  • Storage: ~3KB per job")
    print("\n" + "="*60)

    # Load model
    model = load_model()
    if model is None:
        return False

    # Connect to database
    db = get_database()

    # Get jobs without embeddings
    print(f"\n🔍 Finding jobs without embeddings...")
    jobs = get_jobs_without_embeddings(db, limit)

    if not jobs:
        print("✅ All jobs already have embeddings!")
        print("💡 Nothing to do")
        return True

    print(f"📊 Found {len(jobs)} jobs needing encoding")

    # Estimate time and storage
    estimated_time = (len(jobs) / batch_size) * 2  # ~2 seconds per batch
    estimated_storage = (len(jobs) * 3) / 1024  # ~3KB per job in MB

    print(f"\n⏱️  Estimated time: {estimated_time:.1f} seconds ({estimated_time/60:.1f} minutes)")
    print(f"💾 Estimated storage: {estimated_storage:.1f} MB")

    if not dry_run:
        response = input("\n⚠️  Proceed with encoding? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Encoding cancelled")
            return False

    # Extract titles
    titles = [job['title'] for job in jobs]
    job_ids = [job['id'] for job in jobs]

    # Encode in batches
    print(f"\n⚙️  Encoding {len(jobs)} job titles...")
    start_time = time.time()

    all_embeddings = []
    for i in range(0, len(titles), batch_size):
        batch_start = time.time()
        batch_titles = titles[i:i + batch_size]
        batch_ids = job_ids[i:i + batch_size]

        # Encode batch
        batch_embeddings = model.encode(batch_titles, show_progress_bar=False, convert_to_numpy=True)
        all_embeddings.extend(batch_embeddings)

        # Store batch
        if not dry_run:
            store_embeddings(db, batch_ids, batch_embeddings, dry_run=False)

        batch_time = time.time() - batch_start
        processed = min(i + batch_size, len(titles))
        remaining = len(titles) - processed
        eta = (remaining / batch_size) * batch_time if remaining > 0 else 0

        print(f"  [{processed:4d}/{len(titles)}] Batch {i//batch_size + 1} encoded in {batch_time:.2f}s (ETA: {eta:.1f}s)")

    total_time = time.time() - start_time

    print(f"\n✅ Encoding complete!")
    print(f"   • Total time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    print(f"   • Average: {total_time/len(jobs):.3f}s per job")
    print(f"   • Throughput: {len(jobs)/total_time:.1f} jobs/second")

    if dry_run:
        print(f"\n💡 This was a DRY RUN - no database updates made")
        print(f"💡 Run without --dry-run to store embeddings")
    else:
        # Verify embeddings were stored
        print(f"\n🔍 Verifying storage...")
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE embedding_jobbert_title IS NOT NULL")
        encoded_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_count = cursor.fetchone()[0]
        cursor.close()
        if hasattr(db, '_return_connection'):
            db._return_connection(conn)
        else:
            conn.close()

        print(f"   ✓ Jobs with embeddings: {encoded_count:,} / {total_count:,}")
        print(f"   ✓ Coverage: {encoded_count/total_count*100:.1f}%")

        # Calculate actual storage used
        storage_used = (encoded_count * 3) / 1024  # ~3KB per job in MB
        print(f"   ✓ Storage used: {storage_used:.1f} MB")

    print("\n" + "="*60)
    print("✅ ENCODING COMPLETE")
    print("="*60)

    if not dry_run:
        print("\n💡 Next Steps:")
        print("  1. Update daily cron to encode new jobs")
        print("  2. Update matcher to use pre-encoded embeddings")
        print("  3. Update filter_jobs.py to use embeddings")

    print()
    db.close()
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Encode existing jobs with TechWolf JobBERT-v3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 10 jobs (dry-run)
  python scripts/encode_existing_jobs.py --dry-run --limit 10

  # Encode first 100 jobs
  python scripts/encode_existing_jobs.py --limit 100

  # Encode all jobs
  python scripts/encode_existing_jobs.py

  # Encode all jobs with custom batch size
  python scripts/encode_existing_jobs.py --batch-size 200
        """
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of jobs to encode (default: all)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of jobs to encode per batch (default: 100)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test encoding without storing in database'
    )

    args = parser.parse_args()

    try:
        success = run_encoding(
            limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("💡 Progress has been saved. Run again to continue encoding remaining jobs.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
