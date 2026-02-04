#!/usr/bin/env python3
"""
Backfill normalized skills and competencies into existing jobs.

Re-normalizes ai_competencies and ai_key_skills for every job that has them,
using the current state of skill_canonical_map (DB map) plus the static
fallbacks in skill_normalizer.py.  Jobs whose arrays are already fully
normalized are skipped — the script is fully idempotent.

Usage:
    python scripts/backfill_normalized_skills.py            # commit changes
    python scripts/backfill_normalized_skills.py --dry-run  # preview only
"""
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

from src.analysis.skill_normalizer import normalize_and_deduplicate


BATCH_SIZE = 1000


def run_backfill(dry_run: bool = False):
    print("=" * 70)
    print("BACKFILL NORMALIZED SKILLS")
    print("=" * 70)
    print(f"Dry-run: {dry_run}")
    print()

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = False
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    total_processed = 0
    total_updated = 0
    offset = 0
    t0 = time.time()

    while True:
        # Load batch of jobs that have at least one of the two arrays
        cursor.execute(
            """
            SELECT id, ai_competencies, ai_key_skills
            FROM jobs
            WHERE ai_competencies IS NOT NULL OR ai_key_skills IS NOT NULL
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            (BATCH_SIZE, offset),
        )
        rows = cursor.fetchall()
        if not rows:
            break

        update_batch = []

        for row in rows:
            total_processed += 1
            job_id = row['id']
            orig_comps = row['ai_competencies'] or []
            orig_skills = row['ai_key_skills'] or []

            norm_comps = normalize_and_deduplicate(orig_comps)
            norm_skills = normalize_and_deduplicate(orig_skills)

            if norm_comps != orig_comps or norm_skills != orig_skills:
                update_batch.append((norm_comps, norm_skills, job_id))
                total_updated += 1

                if dry_run and total_updated <= 20:
                    # Show first 20 diffs in dry-run mode
                    if norm_comps != orig_comps:
                        print(f"   job {job_id} competencies:")
                        print(f"      before: {orig_comps}")
                        print(f"      after:  {norm_comps}")
                    if norm_skills != orig_skills:
                        print(f"   job {job_id} skills:")
                        print(f"      before: {orig_skills}")
                        print(f"      after:  {norm_skills}")

        if update_batch and not dry_run:
            cursor.executemany(
                """
                UPDATE jobs
                SET ai_competencies = %s,
                    ai_key_skills   = %s,
                    last_updated    = NOW()
                WHERE id = %s
                """,
                update_batch,
            )
            conn.commit()

        offset += BATCH_SIZE
        elapsed = time.time() - t0
        print(f"   Processed {total_processed} jobs ({total_updated} need update) — {elapsed:.1f}s")

    # Final summary
    print()
    print("=" * 70)
    print(f"DONE — {total_processed} jobs processed, {total_updated} updated")
    if dry_run:
        print("(dry-run — nothing was committed)")
    print("=" * 70)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill normalized skills')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without committing')
    args = parser.parse_args()
    run_backfill(dry_run=args.dry_run)
