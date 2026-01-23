#!/usr/bin/env python3
"""
Backfill Existing Jobs with Full-Text Embeddings from JobBERT-v3

Pre-computes full-text embeddings for all jobs in the database for improved semantic search.

Usage:
    python scripts/backfill_full_text_embeddings.py --dry-run --limit 10
    python scripts/backfill_full_text_embeddings.py --limit 100
    python scripts/backfill_full_text_embeddings.py
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

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
        # Fix for PyTorch 2.9+ compatibility
        model = SentenceTransformer('TechWolf/JobBERT-v3', device='cpu', trust_remote_code=True)
        print("✅ Model loaded successfully")
        return model
    except ImportError:
        print("❌ Error: sentence-transformers package not installed")
        print("   Install with: pip install sentence-transformers")
        return None
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None


def get_jobs_without_full_embeddings(db, limit=None):
    """Get jobs that don't have full-text embeddings yet"""
    conn = db._get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, title, description
        FROM jobs
        WHERE embedding_jobbert_full IS NULL
        ORDER BY discovered_date DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)

    if hasattr(cursor, 'fetchall'):
        rows = cursor.fetchall()
        if rows and not isinstance(rows[0], dict):
            jobs = [{'id': row[0], 'title': row[1], 'description': row[2]} for row in rows]
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


def store_full_embeddings(db, job_ids, embeddings, dry_run=False):
    """Store full-text embeddings in the database"""
    if dry_run:
        return

    conn = db._get_connection()
    cursor = conn.cursor()

    is_postgres = hasattr(db, 'connection_pool') or os.getenv('DATABASE_URL', '').startswith('postgres')

    try:
        for job_id, embedding in zip(job_ids, embeddings):
            embedding_json = json.dumps(embedding.tolist())

            if is_postgres:
                cursor.execute("""
                    UPDATE jobs
                    SET embedding_jobbert_full = %s::jsonb,
                        embedding_date = NOW()
                    WHERE id = %s
                """, (embedding_json, job_id))
            else:
                cursor.execute("""
                    UPDATE jobs
                    SET embedding_jobbert_full = ?,
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


def run_encoding(limit=None, batch_size=32, dry_run=False):
    """Main encoding function"""

    print("\n" + "="*60)
    print("BACKFILL FULL-TEXT EMBEDDINGS - TechWolf JobBERT-v3")
    print("="*60)

    if dry_run:
        print("🔍 DRY RUN MODE - No database updates")
    else:
        print("⚠️  PRODUCTION MODE - Database will be updated")

    print(f"\nConfiguration:")
    print(f"  • Batch size: {batch_size} jobs")
    print(f"  • Limit: {limit if limit else 'All jobs'}")
    print("\n" + "="*60)

    model = load_model()
    if model is None:
        return False

    db = get_database()

    print(f"\n🔍 Finding jobs without full-text embeddings...")
    jobs = get_jobs_without_full_embeddings(db, limit)

    if not jobs:
        print("✅ All jobs already have full-text embeddings!")
        return True

    print(f"📊 Found {len(jobs)} jobs needing encoding")

    if not dry_run:
        response = input("\n⚠️  Proceed with encoding? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Encoding cancelled")
            return False

    job_texts = [f"{job.get('title', '')} {job.get('description', '')}" for job in jobs]
    job_ids = [job['id'] for job in jobs]

    print(f"\n⚙️  Encoding {len(jobs)} job full-texts...")
    start_time = time.time()

    for i in range(0, len(job_texts), batch_size):
        batch_start = time.time()
        batch_texts = job_texts[i:i + batch_size]
        batch_ids = job_ids[i:i + batch_size]

        batch_embeddings = model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)

        if not dry_run:
            store_full_embeddings(db, batch_ids, batch_embeddings, dry_run=False)

        batch_time = time.time() - batch_start
        processed = min(i + batch_size, len(job_texts))
        remaining = len(job_texts) - processed
        eta = (remaining / batch_size) * batch_time if remaining > 0 else 0
        
        print(f"  [{processed:4d}/{len(job_texts)}] Batch {i//batch_size + 1} encoded in {batch_time:.2f}s (ETA: {eta:.1f}s)")

    total_time = time.time() - start_time

    print(f"\n✅ Encoding complete!")
    print(f"   • Total time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    print(f"   • Average: {total_time/len(jobs):.3f}s per job")
    print(f"   • Throughput: {len(jobs)/total_time:.1f} jobs/second")

    if dry_run:
        print(f"\n💡 This was a DRY RUN - no database updates made")
    else:
        print(f"\n🔍 Verifying storage...")
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE embedding_jobbert_full IS NOT NULL")
        encoded_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_count = cursor.fetchone()[0]
        cursor.close()
        if hasattr(db, '_return_connection'):
            db._return_connection(conn)
        else:
            conn.close()

        print(f"   ✓ Jobs with full-text embeddings: {encoded_count:,} / {total_count:,}")
        print(f"   ✓ Coverage: {encoded_count/total_count*100:.1f}%")

    print("\n" + "="*60)
    print("✅ BACKFILL COMPLETE")
    print("="*60)

    db.close()
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Backfill existing jobs with full-text JobBERT-v3 embeddings.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of jobs to encode (default: all)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Number of jobs to encode per batch (default: 32)'
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
        sys.exit(1)


if __name__ == '__main__':
    main()
