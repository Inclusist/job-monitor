"""
Migrate data from SQLite to PostgreSQL

Usage:
    python scripts/migrate_to_postgres.py <postgresql_url>
    
Example:
    python scripts/migrate_to_postgres.py "postgresql://user:pass@host:5432/dbname"
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.operations import JobDatabase
from src.database.postgres_operations import PostgresDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_jobs(sqlite_db: JobDatabase, postgres_db: PostgresDatabase) -> tuple:
    """
    Migrate jobs from SQLite to PostgreSQL
    
    Returns:
        tuple: (migrated_count, skipped_count, error_count)
    """
    logger.info("Starting jobs migration...")
    
    # Get all jobs from SQLite
    conn = sqlite_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs")
    
    jobs = []
    for row in cursor.fetchall():
        jobs.append(dict(row))
    
    conn.close()
    
    logger.info(f"Found {len(jobs)} jobs to migrate")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for job in jobs:
        try:
            # Convert TEXT dates to timestamps if needed
            job_data = {
                'job_id': job['job_id'],
                'source': job['source'],
                'title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'description': job['description'],
                'url': job['url'],
                'posted_date': job['posted_date'],
                'salary': job['salary'],
                'discovered_date': job['discovered_date'],
                'last_updated': job['last_updated'],
                'match_score': job['match_score'],
                'match_reasoning': job['match_reasoning'],
                'key_alignments': job['key_alignments'],
                'potential_gaps': job['potential_gaps'],
                'priority': job['priority'],
                'status': job['status']
            }
            
            result = postgres_db.add_job(job_data)
            if result:
                migrated += 1
                if migrated % 100 == 0:
                    logger.info(f"Migrated {migrated} jobs...")
            else:
                skipped += 1
                
        except Exception as e:
            errors += 1
            logger.error(f"Error migrating job {job['job_id']}: {e}")
    
    logger.info(f"Jobs migration complete: {migrated} migrated, {skipped} skipped, {errors} errors")
    return (migrated, skipped, errors)


def migrate_user_job_matches(sqlite_db: JobDatabase, postgres_db: PostgresDatabase) -> tuple:
    """
    Migrate user job matches from SQLite to PostgreSQL
    
    Returns:
        tuple: (migrated_count, skipped_count, error_count)
    """
    logger.info("Starting user_job_matches migration...")
    
    conn = sqlite_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_job_matches")
    
    matches = []
    for row in cursor.fetchall():
        matches.append(dict(row))
    
    conn.close()
    
    logger.info(f"Found {len(matches)} user job matches to migrate")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for match in matches:
        try:
            # Parse key_alignments and potential_gaps from comma-separated strings
            key_alignments = [x.strip() for x in match['key_alignments'].split(',')] if match['key_alignments'] else []
            potential_gaps = [x.strip() for x in match['potential_gaps'].split(',')] if match['potential_gaps'] else []
            
            result = postgres_db.add_user_job_match(
                user_id=match['user_id'],
                job_id=match['job_id'],
                semantic_score=match['semantic_score'],
                claude_score=match['claude_score'],
                match_reasoning=match['match_reasoning'],
                key_alignments=key_alignments if key_alignments != [''] else None,
                potential_gaps=potential_gaps if potential_gaps != [''] else None,
                priority=match['priority'] or 'medium'
            )
            
            if result:
                migrated += 1
                if migrated % 100 == 0:
                    logger.info(f"Migrated {migrated} matches...")
            else:
                skipped += 1
                
        except Exception as e:
            errors += 1
            logger.error(f"Error migrating match for user {match['user_id']}, job {match['job_id']}: {e}")
    
    logger.info(f"Matches migration complete: {migrated} migrated, {skipped} skipped, {errors} errors")
    return (migrated, skipped, errors)


def migrate_all(sqlite_path: str, postgres_url: str):
    """
    Migrate all data from SQLite to PostgreSQL
    
    Args:
        sqlite_path: Path to SQLite database file
        postgres_url: PostgreSQL connection URL
    """
    logger.info("="*80)
    logger.info("STARTING DATABASE MIGRATION: SQLite → PostgreSQL")
    logger.info(f"Source: {sqlite_path}")
    logger.info(f"Target: {postgres_url[:50]}...")
    logger.info("="*80)
    
    # Initialize databases
    try:
        logger.info("\nConnecting to SQLite database...")
        sqlite_db = JobDatabase(sqlite_path)
        
        logger.info("Connecting to PostgreSQL database...")
        postgres_db = PostgresDatabase(postgres_url)
        
    except Exception as e:
        logger.error(f"Failed to connect to databases: {e}")
        sys.exit(1)
    
    # Migrate jobs
    jobs_migrated, jobs_skipped, jobs_errors = migrate_jobs(sqlite_db, postgres_db)
    
    # Migrate user job matches
    matches_migrated, matches_skipped, matches_errors = migrate_user_job_matches(sqlite_db, postgres_db)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("MIGRATION COMPLETE")
    logger.info("="*80)
    logger.info(f"\nJobs:")
    logger.info(f"  ✓ Migrated: {jobs_migrated}")
    logger.info(f"  ⊘ Skipped:  {jobs_skipped}")
    logger.info(f"  ✗ Errors:   {jobs_errors}")
    
    logger.info(f"\nUser Job Matches:")
    logger.info(f"  ✓ Migrated: {matches_migrated}")
    logger.info(f"  ⊘ Skipped:  {matches_skipped}")
    logger.info(f"  ✗ Errors:   {matches_errors}")
    
    total_migrated = jobs_migrated + matches_migrated
    total_errors = jobs_errors + matches_errors
    
    logger.info(f"\nTotal:")
    logger.info(f"  ✓ Migrated: {total_migrated}")
    logger.info(f"  ✗ Errors:   {total_errors}")
    
    if total_errors == 0:
        logger.info("\n✓ Migration completed successfully!")
    else:
        logger.warning(f"\n⚠ Migration completed with {total_errors} errors")
    
    logger.info("="*80)
    
    # Close connections
    postgres_db.close()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_to_postgres.py <postgresql_url>")
        print("\nExample:")
        print('  python scripts/migrate_to_postgres.py "postgresql://user:pass@host:5432/dbname"')
        print("\nOr with Railway DATABASE_URL:")
        print('  python scripts/migrate_to_postgres.py "$DATABASE_URL"')
        sys.exit(1)
    
    postgres_url = sys.argv[1]
    sqlite_path = os.environ.get('DATABASE_PATH', 'data/jobs.db')
    
    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite database not found: {sqlite_path}")
        sys.exit(1)
    
    # Confirm migration
    print(f"\n⚠️  WARNING: This will migrate data from SQLite to PostgreSQL")
    print(f"   Source: {sqlite_path}")
    print(f"   Target: {postgres_url[:50]}...")
    print(f"\n   Existing data in PostgreSQL will be preserved (duplicates skipped)")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled")
        sys.exit(0)
    
    migrate_all(sqlite_path, postgres_url)


if __name__ == "__main__":
    main()
