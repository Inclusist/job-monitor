#!/usr/bin/env python3
"""
Job Monitoring System - Main Script
Orchestrates daily job searches, analysis, and notifications
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.operations import JobDatabase
from database.cv_operations import CVManager
from analysis.claude_analyzer import ClaudeJobAnalyzer
from collectors.indeed import IndeedCollector
from utils.helpers import (
    setup_logging,
    load_config,
    deduplicate_jobs,
    filter_new_jobs,
    categorize_jobs
)


def main():
    """Main execution function"""
    
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    logger = setup_logging(
        log_file=os.getenv('LOG_FILE', 'data/logs/job_monitor.log'),
        level=os.getenv('LOG_LEVEL', 'INFO')
    )
    
    logger.info("="*60)
    logger.info("Starting Job Monitoring System")
    logger.info(f"Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    try:
        # Load configuration
        config = load_config('config.yaml')
        logger.info("Configuration loaded successfully")
        
        # Initialize database
        db_path = os.getenv('DATABASE_PATH', 'data/jobs.db')
        db = JobDatabase(db_path)
        logger.info(f"Database initialized: {db_path}")

        # Initialize CV Manager
        cv_manager = CVManager(db_path)

        # Get user email (from env var, or use default from config)
        user_email = os.getenv('USER_EMAIL')
        if not user_email:
            # Try to get from config or use default
            profile = config.get('profile', {})
            user_email = profile.get('email', 'default@localhost')

        logger.info(f"Running for user: {user_email}")

        # Get or create user
        user = cv_manager.get_or_create_user(
            email=user_email,
            name=config['profile'].get('name'),
            current_role=config['profile'].get('current_role'),
            location=config['profile'].get('location'),
            preferences=config.get('preferences', {})
        )
        user_id = user['id']
        logger.info(f"User initialized (ID: {user_id})")

        # Get primary CV profile if available
        cv_profile = cv_manager.get_profile_by_user(user_id)

        # Get initial statistics
        initial_stats = db.get_statistics()
        logger.info(f"Current database: {initial_stats['total_jobs']} total jobs")
        
        # Initialize collectors
        indeed_publisher_id = os.getenv('INDEED_PUBLISHER_ID')
        if not indeed_publisher_id or indeed_publisher_id == 'your_publisher_id_here':
            logger.error("INDEED_PUBLISHER_ID not configured in .env file")
            logger.info("Please sign up at https://www.indeed.com/publisher")
            return
        
        indeed = IndeedCollector(indeed_publisher_id)
        logger.info("Indeed collector initialized")
        
        # Collect jobs from Indeed
        logger.info("Starting job collection from Indeed...")
        search_config = config['search_config']
        
        indeed_jobs = indeed.search_multiple(
            queries=search_config['keywords'],
            locations=search_config['locations'],
            days_back=1,  # Jobs from last 24 hours
            limit=25
        )
        
        logger.info(f"Collected {len(indeed_jobs)} jobs from Indeed")
        
        # Combine all jobs (for now just Indeed, will add LinkedIn later)
        all_jobs = indeed_jobs
        
        # Deduplicate
        all_jobs = deduplicate_jobs(all_jobs)
        logger.info(f"After deduplication: {len(all_jobs)} unique jobs")
        
        # Filter new jobs only
        new_jobs = filter_new_jobs(all_jobs, db)
        logger.info(f"Found {len(new_jobs)} new jobs")
        
        if not new_jobs:
            logger.info("No new jobs found. Exiting.")
            db.close()
            return
        
        # Initialize Claude analyzer
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_key or anthropic_key == 'your_claude_api_key_here':
            logger.error("ANTHROPIC_API_KEY not configured in .env file")
            logger.info("Please get your API key from https://console.anthropic.com/")
            db.close()
            return
        
        analyzer = ClaudeJobAnalyzer(anthropic_key, model="claude-3-5-haiku-20241022")

        # Use CV profile if available, otherwise fallback to config.yaml
        if cv_profile:
            analyzer.set_profile_from_cv(cv_profile)
            logger.info(f"Using CV profile for analysis (uploaded: {cv_profile.get('uploaded_date', 'N/A')[:10]})")
        else:
            analyzer.set_profile(config['profile'])
            logger.info("Using config.yaml profile (no CV uploaded)")
            logger.info("💡 Tip: Upload your CV with: python scripts/cv_cli.py upload --email your@email.com --file your_cv.pdf")

        logger.info("Claude analyzer initialized (using Haiku model for cost efficiency)")
        
        # Analyze jobs
        logger.info("Starting job analysis with Claude...")
        analyzed_jobs = analyzer.analyze_batch(new_jobs)
        logger.info(f"Analysis complete for {len(analyzed_jobs)} jobs")
        
        # Store jobs in database with user association
        logger.info("Storing jobs in database...")
        stored_count = 0
        for job in analyzed_jobs:
            # Add user and CV profile references
            job['user_id'] = user_id
            if cv_profile:
                job['cv_profile_id'] = cv_profile.get('id')

            job_id = db.add_job(job)
            if job_id:
                stored_count += 1
        
        logger.info(f"Stored {stored_count} new jobs in database")
        
        # Categorize jobs
        categorized = categorize_jobs(analyzed_jobs)
        
        logger.info("\n" + "="*60)
        logger.info("JOB ANALYSIS SUMMARY")
        logger.info("="*60)
        logger.info(f"High Priority (85+): {len(categorized['high'])} jobs")
        logger.info(f"Medium Priority (70-84): {len(categorized['medium'])} jobs")
        logger.info(f"Low Priority (<70): {len(categorized['low'])} jobs")
        
        # Display high priority jobs
        if categorized['high']:
            logger.info("\n🔥 HIGH PRIORITY JOBS:")
            for i, job in enumerate(categorized['high'][:5], 1):
                logger.info(f"\n{i}. {job['title']} at {job['company']}")
                logger.info(f"   Score: {job['match_score']} | Location: {job['location']}")
                logger.info(f"   Reasoning: {job['reasoning']}")
                logger.info(f"   URL: {job['url']}")
        
        # Get final statistics
        final_stats = db.get_statistics()
        logger.info(f"\n📊 Database now contains {final_stats['total_jobs']} total jobs")
        
        # TODO: Send email digest (implement in next step)
        logger.info("\n📧 Email digest generation (to be implemented)")
        
        logger.info("\n" + "="*60)
        logger.info("Job monitoring completed successfully!")
        logger.info("="*60)
        
        # Close database
        db.close()
        cv_manager.close()
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
