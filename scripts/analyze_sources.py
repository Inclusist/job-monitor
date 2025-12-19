#!/usr/bin/env python3
"""
Analyze Job Sources in Database
Shows source quality statistics and allows filtering existing jobs
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.operations import JobDatabase
from collectors.source_filter import SourceFilter


def analyze_sources(db_path: str):
    """Analyze job sources in the database"""
    
    db = JobDatabase(db_path)
    source_filter = SourceFilter()
    
    # Get all jobs
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, url, company, title FROM jobs')
    jobs = cursor.fetchall()
    
    print(f"\n{'='*80}")
    print(f"JOB SOURCE QUALITY ANALYSIS")
    print(f"{'='*80}")
    print(f"Total jobs in database: {len(jobs)}\n")
    
    # Analyze sources
    domain_stats = {}
    low_quality_jobs = []
    medium_quality_jobs = []
    high_quality_jobs = []
    
    for job_id, url, company, title in jobs:
        domain = source_filter.get_domain(url)
        quality = source_filter.get_quality_score(url)
        
        if domain:
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'count': 0,
                    'quality': quality,
                    'is_blacklisted': source_filter.is_blacklisted(url),
                    'is_whitelisted': source_filter.is_whitelisted(url),
                    'jobs': []
                }
            domain_stats[domain]['count'] += 1
            domain_stats[domain]['jobs'].append((job_id, company, title))
        
        if quality == 1:
            low_quality_jobs.append((job_id, domain, company, title))
        elif quality == 2:
            medium_quality_jobs.append((job_id, domain, company, title))
        else:
            high_quality_jobs.append((job_id, domain, company, title))
    
    # Sort domains by count
    sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    # Display statistics
    print(f"QUALITY BREAKDOWN:")
    print(f"  High quality (trusted):     {len(high_quality_jobs):3d} jobs")
    print(f"  Medium quality (neutral):   {len(medium_quality_jobs):3d} jobs")
    print(f"  Low quality (spam/blocked): {len(low_quality_jobs):3d} jobs")
    print()
    
    # Show top domains
    print(f"\nTOP JOB SOURCES:")
    print(f"{'-'*80}")
    print(f"{'Count':<6} {'Quality':<8} {'Status':<15} {'Domain'}")
    print(f"{'-'*80}")
    
    for domain, stats in sorted_domains[:25]:
        count = stats['count']
        quality = stats['quality']
        
        if stats['is_blacklisted']:
            status = '🚫 BLACKLISTED'
            quality_str = f"{quality}/3 ⚠️"
        elif stats['is_whitelisted']:
            status = '✅ TRUSTED'
            quality_str = f"{quality}/3 ⭐"
        else:
            status = '⚪ NEUTRAL'
            quality_str = f"{quality}/3"
        
        print(f"{count:<6} {quality_str:<8} {status:<15} {domain}")
    
    # Show blacklisted domains with job counts
    print(f"\n\nBLACKLISTED DOMAINS IN YOUR DATABASE:")
    print(f"{'-'*80}")
    
    blacklisted = [(d, s) for d, s in sorted_domains if s['is_blacklisted']]
    if blacklisted:
        for domain, stats in blacklisted:
            print(f"  {stats['count']:3d} jobs from {domain}")
            # Show first 3 jobs as examples
            for job_id, company, title in stats['jobs'][:3]:
                print(f"      - {title[:60]} at {company}")
            if len(stats['jobs']) > 3:
                print(f"      ... and {len(stats['jobs']) - 3} more")
            print()
    else:
        print("  None found! ✓")
    
    conn.close()
    
    return low_quality_jobs, domain_stats


def delete_low_quality_jobs(db_path: str, dry_run: bool = True):
    """Delete jobs from blacklisted sources"""
    
    db = JobDatabase(db_path)
    source_filter = SourceFilter()
    
    conn = db._get_connection()
    cursor = conn.cursor()
    
    # Get jobs from blacklisted sources
    cursor.execute('SELECT id, url, company, title FROM jobs')
    jobs = cursor.fetchall()
    
    to_delete = []
    for job_id, url, company, title in jobs:
        if source_filter.is_blacklisted(url):
            to_delete.append((job_id, source_filter.get_domain(url), company, title))
    
    print(f"\n{'='*80}")
    print(f"DELETE LOW-QUALITY JOBS")
    print(f"{'='*80}")
    print(f"Found {len(to_delete)} jobs from blacklisted sources\n")
    
    if not to_delete:
        print("No low-quality jobs to delete! ✓")
        conn.close()
        return
    
    # Show what will be deleted
    domains = {}
    for job_id, domain, company, title in to_delete:
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(title)
    
    print("Jobs to be deleted by domain:")
    for domain, titles in sorted(domains.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {len(titles):3d} jobs from {domain}")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN MODE - No jobs will be deleted")
        print("Run with --confirm to actually delete these jobs")
    else:
        # Delete jobs
        print(f"\n🗑️  Deleting {len(to_delete)} jobs...")
        for job_id, domain, company, title in to_delete:
            cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
        
        conn.commit()
        print(f"✓ Deleted {len(to_delete)} low-quality jobs")
    
    conn.close()


def main():
    """Main function"""
    load_dotenv()
    
    db_path = os.getenv('DATABASE_PATH', 'data/jobs.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return
    
    # Analyze sources
    low_quality_jobs, domain_stats = analyze_sources(db_path)
    
    # Ask if user wants to delete low-quality jobs
    if low_quality_jobs:
        print(f"\n\n{'='*80}")
        print("OPTIONS:")
        print("  1. Keep all jobs (do nothing)")
        print("  2. Delete low-quality jobs (dry run - see what would be deleted)")
        print("  3. Delete low-quality jobs (CONFIRM - actually delete)")
        print(f"{'='*80}")
        
        if '--confirm' in sys.argv:
            delete_low_quality_jobs(db_path, dry_run=False)
        elif '--dry-run' in sys.argv or '--delete' in sys.argv:
            delete_low_quality_jobs(db_path, dry_run=True)
        else:
            print("\nTo delete low-quality jobs:")
            print("  python scripts/analyze_sources.py --dry-run    (preview)")
            print("  python scripts/analyze_sources.py --confirm    (delete)")


if __name__ == '__main__':
    main()
