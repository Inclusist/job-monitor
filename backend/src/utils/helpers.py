"""
Utility functions for job monitoring system
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any
import yaml


def setup_logging(log_file: str = "data/logs/job_monitor.log", level: str = "INFO"):
    """Configure logging"""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate jobs based on job_id or external_id.
    Ensures all jobs have a job_id field.
    
    Args:
        jobs: List of job dictionaries
        
    Returns:
        Deduplicated list of jobs with job_id normalized
    """
    seen = set()
    unique_jobs = []
    
    for job in jobs:
        # Try multiple ID fields for different sources
        job_id = job.get('job_id') or job.get('external_id') or job.get('url')
        if job_id and job_id not in seen:
            seen.add(job_id)
            # Ensure job_id is set for database consistency
            if not job.get('job_id') and job.get('external_id'):
                job['job_id'] = job['external_id']
            unique_jobs.append(job)
    
    return unique_jobs


def filter_new_jobs(jobs: List[Dict[str, Any]], db) -> List[Dict[str, Any]]:
    """
    Filter out jobs that already exist in database OR have been deleted
    
    Args:
        jobs: List of job dictionaries
        db: JobDatabase instance
        
    Returns:
        List of new jobs only (excluding previously deleted jobs)
    """
    new_jobs = []
    
    # Get list of deleted job_ids to exclude
    deleted_job_ids = db.get_deleted_job_ids()
    
    for job in jobs:
        job_id = job.get('job_id')
        # Skip if job already exists OR was previously deleted
        if not db.job_exists(job_id) and job_id not in deleted_job_ids:
            new_jobs.append(job)
        elif job_id in deleted_job_ids:
            print(f"  Skipping previously deleted job: {job.get('title')} at {job.get('company')}")
    
    return new_jobs


def categorize_jobs(jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize jobs by priority
    
    Args:
        jobs: List of analyzed job dictionaries
        
    Returns:
        Dictionary with 'high', 'medium', 'low' priority lists
    """
    categorized = {
        'high': [],
        'medium': [],
        'low': []
    }
    
    for job in jobs:
        priority = job.get('priority', 'low')
        if priority in categorized:
            categorized[priority].append(job)
    
    # Sort each category by match score
    for priority in categorized:
        categorized[priority].sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    return categorized


def format_date(date_str: str) -> str:
    """Format date string for display"""
    try:
        if date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
    except:
        pass
    return date_str or 'Unknown'


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'


if __name__ == "__main__":
    # Test utilities
    print("Testing utilities...")
    
    # Test deduplication
    test_jobs = [
        {'job_id': '1', 'title': 'Job 1'},
        {'job_id': '2', 'title': 'Job 2'},
        {'job_id': '1', 'title': 'Job 1 Duplicate'},
    ]
    
    unique = deduplicate_jobs(test_jobs)
    print(f"Deduplication: {len(test_jobs)} -> {len(unique)} jobs")
    
    # Test categorization
    test_jobs_with_priority = [
        {'job_id': '1', 'title': 'Job 1', 'priority': 'high', 'match_score': 95},
        {'job_id': '2', 'title': 'Job 2', 'priority': 'high', 'match_score': 88},
        {'job_id': '3', 'title': 'Job 3', 'priority': 'medium', 'match_score': 75},
        {'job_id': '4', 'title': 'Job 4', 'priority': 'low', 'match_score': 60},
    ]
    
    categorized = categorize_jobs(test_jobs_with_priority)
    print(f"Categorization:")
    print(f"  High: {len(categorized['high'])} jobs")
    print(f"  Medium: {len(categorized['medium'])} jobs")
    print(f"  Low: {len(categorized['low'])} jobs")
    
    print("Utilities test complete!")
