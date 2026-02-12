"""
Duplicate job detection and merging utility

Detects duplicate job postings using title embedding similarity and company matching.
Merges locations from duplicate postings into a single canonical job.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def detect_duplicate_groups(
    jobs: List[Dict],
    similarity_threshold: float = 0.98
) -> Dict[int, List[int]]:
    """
    Detect duplicate job groups using title embedding similarity and company matching.
    
    Algorithm:
    1. Group jobs by company (exact match)
    2. Within each company, calculate title embedding similarity
    3. Jobs with similarity >= threshold are considered duplicates
    
    Args:
        jobs: List of job dicts with keys: id, company, title, embedding_jobbert_title
        similarity_threshold: Cosine similarity threshold (default: 0.98)
        
    Returns:
        Dict mapping canonical_job_id -> [duplicate_job_ids]
        
    Example:
        {
            12345: [12346, 12347],  # Job 12345 has 2 duplicates
            12350: [12351]           # Job 12350 has 1 duplicate
        }
    """
    if not jobs:
        return {}
    
    logger.info(f"Detecting duplicates in {len(jobs)} jobs (threshold: {similarity_threshold})")
    
    # Group by company first (exact match)
    company_groups = defaultdict(list)
    for job in jobs:
        company = job.get('company', '').strip()
        if company and job.get('embedding_jobbert_title'):
            company_groups[company].append(job)
    
    logger.info(f"Grouped into {len(company_groups)} companies")
    
    # Find duplicates within each company
    duplicate_groups = {}
    total_duplicates = 0
    
    for company, company_jobs in company_groups.items():
        if len(company_jobs) < 2:
            continue
        
        # Extract embeddings
        embeddings = np.array([job['embedding_jobbert_title'] for job in company_jobs])
        
        # Calculate pairwise cosine similarity
        similarities = cosine_similarity(embeddings)
        
        # Find duplicates (similarity >= threshold)
        processed = set()
        for i in range(len(company_jobs)):
            if i in processed:
                continue
            
            duplicates = []
            for j in range(i + 1, len(company_jobs)):
                if j in processed:
                    continue
                    
                if similarities[i][j] >= similarity_threshold:
                    duplicates.append(j)
                    processed.add(j)
            
            if duplicates:
                canonical_id = company_jobs[i]['id']
                duplicate_ids = [company_jobs[j]['id'] for j in duplicates]
                duplicate_groups[canonical_id] = duplicate_ids
                total_duplicates += len(duplicate_ids)
                
                logger.debug(
                    f"Found duplicate group: {company_jobs[i]['title'][:50]} "
                    f"({len(duplicates)} duplicates)"
                )
    
    logger.info(
        f"Detected {len(duplicate_groups)} duplicate groups "
        f"with {total_duplicates} total duplicates"
    )
    
    return duplicate_groups


def merge_locations(
    canonical_job: Dict,
    duplicate_jobs: List[Dict]
) -> Tuple[List[str], List[str]]:
    """
    Merge location data from duplicate jobs into canonical job.
    
    Args:
        canonical_job: The canonical job dict
        duplicate_jobs: List of duplicate job dicts
        
    Returns:
        Tuple of (merged_locations, merged_cities)
    """
    all_locations = set()
    all_cities = set()
    
    # Add canonical job locations
    if canonical_job.get('location'):
        all_locations.add(canonical_job['location'])
    
    for loc in canonical_job.get('locations_derived', []) or []:
        if loc:
            all_locations.add(loc)
    
    for city in canonical_job.get('cities_derived', []) or []:
        if city:
            all_cities.add(city)
    
    # Add duplicate job locations
    for dup_job in duplicate_jobs:
        if dup_job.get('location'):
            all_locations.add(dup_job['location'])
        
        for loc in dup_job.get('locations_derived', []) or []:
            if loc:
                all_locations.add(loc)
        
        for city in dup_job.get('cities_derived', []) or []:
            if city:
                all_cities.add(city)
    
    return sorted(list(all_locations)), sorted(list(all_cities))


def run_duplicate_detection(
    db,
    limit: Optional[int] = None,
    similarity_threshold: float = 0.98,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Main entry point for duplicate detection and merging.
    
    Args:
        db: Database instance (PostgresDatabase)
        limit: Optional limit on number of jobs to process
        similarity_threshold: Cosine similarity threshold (default: 0.98)
        dry_run: If True, only detect duplicates without merging
        
    Returns:
        Dict with statistics: {
            'jobs_analyzed': int,
            'duplicate_groups': int,
            'duplicates_merged': int,
            'locations_merged': int
        }
    """
    logger.info("Starting duplicate detection...")
    
    # Fetch jobs with embeddings
    jobs = db.get_jobs_for_duplicate_detection(limit=limit)
    
    if not jobs:
        logger.warning("No jobs found for duplicate detection")
        return {
            'jobs_analyzed': 0,
            'duplicate_groups': 0,
            'duplicates_merged': 0,
            'locations_merged': 0
        }
    
    # Detect duplicates
    duplicate_groups = detect_duplicate_groups(jobs, similarity_threshold)
    
    if not duplicate_groups:
        logger.info("No duplicates detected")
        return {
            'jobs_analyzed': len(jobs),
            'duplicate_groups': 0,
            'duplicates_merged': 0,
            'locations_merged': 0
        }
    
    if dry_run:
        total_duplicates = sum(len(dups) for dups in duplicate_groups.values())
        logger.info(f"DRY RUN: Would merge {total_duplicates} duplicates")
        return {
            'jobs_analyzed': len(jobs),
            'duplicate_groups': len(duplicate_groups),
            'duplicates_merged': 0,
            'locations_merged': 0
        }
    
    # Merge duplicates
    duplicates_merged = 0
    locations_merged = 0
    
    # Create job lookup
    job_lookup = {job['id']: job for job in jobs}
    
    for canonical_id, duplicate_ids in duplicate_groups.items():
        canonical_job = job_lookup.get(canonical_id)
        duplicate_jobs = [job_lookup.get(dup_id) for dup_id in duplicate_ids if dup_id in job_lookup]
        
        if not canonical_job or not duplicate_jobs:
            continue
        
        # Merge locations
        merged_locations, merged_cities = merge_locations(canonical_job, duplicate_jobs)
        
        # Update database
        success = db.merge_job_locations(
            canonical_id=canonical_id,
            duplicate_ids=duplicate_ids,
            merged_locations=merged_locations,
            merged_cities=merged_cities
        )
        
        if success:
            duplicates_merged += len(duplicate_ids)
            locations_merged += len(merged_locations)
    
    logger.info(
        f"Merged {duplicates_merged} duplicates into {len(duplicate_groups)} canonical jobs"
    )
    
    return {
        'jobs_analyzed': len(jobs),
        'duplicate_groups': len(duplicate_groups),
        'duplicates_merged': duplicates_merged,
        'locations_merged': locations_merged
    }
