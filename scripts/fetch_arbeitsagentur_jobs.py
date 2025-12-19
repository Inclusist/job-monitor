"""
Bulk fetch jobs from Bundesagentur für Arbeit (German Federal Employment Agency)

This script collects jobs from the official German government job database and
stores them in the local database.
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.arbeitsagentur import ArbeitsagenturCollector
from src.database.factory import get_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_arbeitsagentur_jobs(
    keywords=None,
    location=None,
    max_results=1000,
    work_time=None,
    days_since_posted=30
):
    """
    Fetch jobs from Arbeitsagentur and store in database
    
    Args:
        keywords: Job search terms (e.g., "Python", "Data Science")
        location: German city or region (e.g., "Berlin", "München")
        max_results: Maximum number of jobs to fetch
        work_time: Work time filter (vz=fulltime, tz=parttime, ho=remote)
        days_since_posted: Only jobs posted in last N days
    
    Returns:
        Number of jobs successfully added
    """
    logger.info(f"Starting Arbeitsagentur job collection")
    logger.info(f"Parameters: keywords={keywords}, location={location}, max_results={max_results}")
    
    # Initialize collector and database
    collector = ArbeitsagenturCollector()
    db = get_database()  # Auto-detects SQLite or PostgreSQL
    
    # Search and parse jobs
    try:
        jobs = collector.search_and_parse(
            keywords=keywords,
            location=location,
            max_results=max_results,
            work_time=work_time,
            days_since_posted=days_since_posted
        )
        
        logger.info(f"Retrieved {len(jobs)} jobs from Arbeitsagentur")
        
        # Add jobs to database
        added_count = 0
        updated_count = 0
        error_count = 0
        
        for job in jobs:
            try:
                # Prepare job data dict for database
                job_data = {
                    'job_id': job['job_id'],
                    'source': job['source'],
                    'title': job['title'],
                    'company': job['company'],
                    'location': job['location'],
                    'description': job['description'],
                    'url': job['url'],
                    'posted_date': job['date_posted'],
                    'salary': job.get('salary', ''),
                    'discovered_date': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
                
                result = db.add_job(job_data)
                
                if result:
                    added_count += 1
                else:
                    updated_count += 1
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Error adding job {job['job_id']}: {e}")
        
        logger.info(f"Database operations: {added_count} added, {updated_count} updated, {error_count} errors")
        
        return added_count
        
    except Exception as e:
        logger.error(f"Error during job collection: {e}")
        return 0


def main():
    """Main entry point for bulk job collection"""
    
    # Define search configurations
    searches = [
        # Software Development jobs
        {
            'keywords': 'Software Developer',
            'location': None,  # All of Germany
            'max_results': 500,
            'work_time': None,
            'days_since_posted': 30
        },
        {
            'keywords': 'Python',
            'location': 'Berlin',
            'max_results': 200,
            'work_time': None,
            'days_since_posted': 30
        },
        {
            'keywords': 'Data Science',
            'location': 'München',
            'max_results': 200,
            'work_time': None,
            'days_since_posted': 30
        },
        # Remote jobs
        {
            'keywords': 'Software',
            'location': None,
            'max_results': 300,
            'work_time': ArbeitsagenturCollector.WORK_TIME_HOME_OFFICE,
            'days_since_posted': 30
        },
        # Full-time IT jobs in major cities
        {
            'keywords': 'Informatiker',
            'location': 'Hamburg',
            'max_results': 200,
            'work_time': ArbeitsagenturCollector.WORK_TIME_FULLTIME,
            'days_since_posted': 30
        },
        {
            'keywords': 'IT',
            'location': 'Frankfurt',
            'max_results': 200,
            'work_time': ArbeitsagenturCollector.WORK_TIME_FULLTIME,
            'days_since_posted': 30
        },
    ]
    
    logger.info("="*80)
    logger.info("STARTING ARBEITSAGENTUR BULK JOB COLLECTION")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info(f"Number of searches: {len(searches)}")
    logger.info("="*80)
    
    total_added = 0
    
    for i, search_config in enumerate(searches, 1):
        logger.info(f"\n[Search {i}/{len(searches)}]")
        added = fetch_arbeitsagentur_jobs(**search_config)
        total_added += added
        logger.info(f"Search {i} complete: {added} new jobs added")
    
    logger.info("\n" + "="*80)
    logger.info(f"COLLECTION COMPLETE")
    logger.info(f"Total new jobs added: {total_added}")
    logger.info("="*80)


if __name__ == "__main__":
    main()
