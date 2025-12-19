"""
Database factory - automatically selects SQLite or PostgreSQL based on environment
"""

import os
import logging
from typing import Union

logger = logging.getLogger(__name__)


def get_database():
    """
    Get database instance based on environment configuration
    
    Returns SQLite for local development, PostgreSQL for production
    
    Returns:
        Union[JobDatabase, PostgresDatabase]: Database instance
    """
    # Check for PostgreSQL connection string (Railway/production)
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgres'):
        logger.info("Using PostgreSQL database")
        from src.database.postgres_operations import PostgresDatabase
        return PostgresDatabase(database_url)
    else:
        logger.info("Using SQLite database")
        from src.database.operations import JobDatabase
        db_path = os.environ.get('DATABASE_PATH', 'data/jobs.db')
        return JobDatabase(db_path)


# Convenience exports
__all__ = ['get_database']
