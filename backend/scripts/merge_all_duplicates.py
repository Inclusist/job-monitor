#!/usr/bin/env python3
"""
Standalone script to detect and merge duplicate jobs in the database.

This script can be run independently to:
1. Detect duplicate job postings using title embeddings
2. Merge locations from duplicates into canonical jobs
3. Mark duplicates as hidden

Usage:
    python scripts/merge_all_duplicates.py [--dry-run] [--limit N] [--threshold 0.98]
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
from src.database.factory import get_database
from src.utils.duplicate_detector import run_duplicate_detection

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description='Detect and merge duplicate job postings'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only detect duplicates without merging'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of jobs to process (default: all)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.98,
        help='Similarity threshold for duplicate detection (default: 0.98)'
    )
    
    args = parser.parse_args()
    
    print('🔍 Duplicate Job Detection and Merging')
    print('=' * 80)
    
    if args.dry_run:
        print('⚠️  DRY RUN MODE - No changes will be made')
        print()
    
    print(f'Settings:')
    print(f'  Similarity threshold: {args.threshold}')
    print(f'  Job limit: {args.limit or "None (all jobs)"}')
    print()
    
    # Get database connection
    db = get_database()
    
    try:
        # Run duplicate detection
        stats = run_duplicate_detection(
            db=db,
            limit=args.limit,
            similarity_threshold=args.threshold,
            dry_run=args.dry_run
        )
        
        # Print results
        print()
        print('📊 Results:')
        print('=' * 80)
        print(f'  Jobs analyzed: {stats["jobs_analyzed"]}')
        print(f'  Duplicate groups found: {stats["duplicate_groups"]}')
        print(f'  Duplicates merged: {stats["duplicates_merged"]}')
        print(f'  Total locations merged: {stats["locations_merged"]}')
        
        if stats['duplicate_groups'] > 0:
            reduction_pct = (stats['duplicates_merged'] / stats['jobs_analyzed']) * 100
            print(f'  Reduction: {reduction_pct:.1f}%')
        
        print()
        
        if args.dry_run and stats['duplicate_groups'] > 0:
            print('✅ Dry run complete. Run without --dry-run to apply changes.')
        elif stats['duplicates_merged'] > 0:
            print('✅ Duplicate merging complete!')
        else:
            print('ℹ️  No duplicates found.')
    
    finally:
        db.close()


if __name__ == '__main__':
    main()
