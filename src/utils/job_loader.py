"""
Automatic job loader for new users and updated search preferences

This module provides functions to automatically load jobs from Arbeitsagentur
when users register or update their search preferences.
"""

import logging
import threading
from typing import List, Optional
from src.collectors.arbeitsagentur import ArbeitsagenturCollector

logger = logging.getLogger(__name__)


def load_jobs_for_combinations(
    keywords: List[str],
    locations: List[str],
    job_db,
    days_since_posted: int = 30,
    background: bool = True
) -> Optional[dict]:
    """
    Load jobs from Arbeitsagentur for given keyword+location combinations

    Args:
        keywords: List of job search keywords
        locations: List of locations to search
        job_db: Database manager instance
        days_since_posted: Number of days to look back (default: 30)
        background: Run in background thread (default: True)

    Returns:
        If background=False, returns stats dict. If background=True, returns None.
    """
    if background:
        # Run in background thread
        thread = threading.Thread(
            target=_load_jobs_sync,
            args=(keywords, locations, job_db, days_since_posted),
            daemon=True
        )
        thread.start()
        logger.info(f"Started background job loading for {len(keywords)} keywords × {len(locations)} locations")
        return None
    else:
        # Run synchronously
        return _load_jobs_sync(keywords, locations, job_db, days_since_posted)


def _load_jobs_sync(
    keywords: List[str],
    locations: List[str],
    job_db,
    days_since_posted: int = 30
) -> dict:
    """
    Synchronously load jobs (internal function)

    Returns:
        dict with stats: {
            'total_searched': int,
            'total_fetched': int,
            'total_stored': int,
            'failed': int
        }
    """
    logger.info(f"Loading jobs for {len(keywords)} keywords × {len(locations)} locations")

    collector = ArbeitsagenturCollector()

    stats = {
        'total_searched': 0,
        'total_fetched': 0,
        'total_stored': 0,
        'failed': 0
    }

    for keyword in keywords:
        for location in locations:
            stats['total_searched'] += 1

            try:
                logger.info(f"Fetching: {keyword} in {location}")

                result = collector.search_jobs(
                    keywords=keyword,
                    location=location,
                    days_since_posted=days_since_posted,
                    page_size=100,
                    page=1
                )

                if not result.get('success'):
                    logger.warning(f"Search failed for {keyword} in {location}: {result.get('message')}")
                    stats['failed'] += 1
                    continue

                jobs = result.get('stellenangebote', [])
                stats['total_fetched'] += len(jobs)

                # Parse and store jobs
                stored_count = 0
                for job_data in jobs:
                    try:
                        parsed_job = collector.parse_job(job_data)
                        if parsed_job:
                            job_db.add_job(parsed_job)
                            stored_count += 1
                    except Exception as e:
                        logger.error(f"Error storing job: {e}")
                        continue

                stats['total_stored'] += stored_count
                logger.info(f"Stored {stored_count}/{len(jobs)} jobs for {keyword} in {location}")

            except Exception as e:
                logger.error(f"Error fetching jobs for {keyword} in {location}: {e}")
                stats['failed'] += 1

    logger.info(f"Job loading complete: {stats}")
    return stats


def trigger_new_user_job_load(
    user_id: int,
    keywords: List[str],
    locations: List[str],
    job_db,
    cv_manager=None
) -> None:
    """
    Trigger automatic job loading for a newly registered user

    This function should be called after user registration completes.

    Args:
        user_id: ID of newly registered user
        keywords: User's search keywords (or defaults)
        locations: User's search locations (or defaults)
        job_db: Database manager instance
        cv_manager: Optional CV manager for tracking
    """
    logger.info(f"Triggering job load for new user {user_id}")

    if not keywords or not locations:
        logger.warning(f"User {user_id} has no keywords/locations, skipping job load")
        return

    # Load jobs in background (non-blocking)
    load_jobs_for_combinations(
        keywords=keywords,
        locations=locations,
        job_db=job_db,
        days_since_posted=30,
        background=True
    )

    logger.info(f"Job loading triggered for user {user_id}: {len(keywords)} keywords × {len(locations)} locations")


def trigger_preferences_update_job_load(
    user_id: int,
    old_keywords: List[str],
    old_locations: List[str],
    new_keywords: List[str],
    new_locations: List[str],
    job_db
) -> None:
    """
    Trigger automatic job loading when user updates search preferences

    Only loads jobs for NEW combinations (not already covered by old preferences).

    Args:
        user_id: User ID
        old_keywords: Previous keywords
        old_locations: Previous locations
        new_keywords: Updated keywords
        new_locations: Updated locations
        job_db: Database manager instance
    """
    logger.info(f"Checking for new combinations for user {user_id}")

    # Find new keywords and locations
    new_kw_set = set(new_keywords) - set(old_keywords)
    new_loc_set = set(new_locations) - set(old_locations)

    # Determine what combinations to fetch
    # Case 1: New keywords added → fetch for ALL locations (old + new)
    # Case 2: New locations added → fetch for ALL keywords (old + new)
    # Case 3: Both changed → fetch all new combinations

    keywords_to_fetch = []
    locations_to_fetch = []

    if new_kw_set:
        # New keywords: fetch them with all locations
        keywords_to_fetch.extend(list(new_kw_set))
        locations_to_fetch = new_locations
        logger.info(f"New keywords detected: {list(new_kw_set)}")

    if new_loc_set:
        # New locations: fetch them with all keywords
        # But avoid duplicates if we already added new keywords
        if not new_kw_set:
            keywords_to_fetch = new_keywords
        else:
            # Add old keywords with new locations (new keywords already covered)
            old_kw_set = set(old_keywords)
            keywords_to_fetch.extend(list(old_kw_set))

        if not locations_to_fetch:
            locations_to_fetch = list(new_loc_set)
        else:
            # Merge new locations
            locations_to_fetch = list(set(locations_to_fetch) | new_loc_set)

        logger.info(f"New locations detected: {list(new_loc_set)}")

    if not keywords_to_fetch or not locations_to_fetch:
        logger.info(f"No new combinations for user {user_id}, skipping job load")
        return

    # Remove duplicates
    keywords_to_fetch = list(set(keywords_to_fetch))
    locations_to_fetch = list(set(locations_to_fetch))

    logger.info(f"Loading jobs for {len(keywords_to_fetch)} keywords × {len(locations_to_fetch)} locations")

    # Load jobs in background
    load_jobs_for_combinations(
        keywords=keywords_to_fetch,
        locations=locations_to_fetch,
        job_db=job_db,
        days_since_posted=30,
        background=True
    )


def get_default_preferences(config_path: str = 'config.yaml') -> dict:
    """
    Get default keywords and locations from config.yaml

    Args:
        config_path: Path to config file

    Returns:
        dict with 'keywords' and 'locations' keys
    """
    import yaml
    from pathlib import Path

    config_file = Path(config_path)
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_path}")
        return {'keywords': [], 'locations': []}

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    return {
        'keywords': config.get('search_config', {}).get('keywords', []),
        'locations': config.get('search_config', {}).get('locations', [])
    }
