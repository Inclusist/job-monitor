#!/usr/bin/env python3
"""
Mass Load Jobs from Bundesagentur für Arbeit (German Federal Employment Agency)

This script efficiently bulk loads jobs from the German government job database.
Features:
- Batch loading with progress tracking
- Multiple search strategies (location-based, keyword-based, comprehensive)
- Duplicate detection
- Resume capability
- Database integration

Usage:
    python scripts/mass_load_arbeitsagentur.py --strategy comprehensive --max-jobs 5000
    python scripts/mass_load_arbeitsagentur.py --strategy locations --max-jobs 2000
    python scripts/mass_load_arbeitsagentur.py --strategy keywords --keywords "Python,Java,Data"
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.arbeitsagentur import ArbeitsagenturCollector
from src.database.postgres_operations import PostgreSQLDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# German cities by population for location-based search
MAJOR_CITIES = [
    "Berlin", "Hamburg", "München", "Köln", "Frankfurt", 
    "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig",
    "Bremen", "Dresden", "Hannover", "Nürnberg", "Duisburg",
    "Bochum", "Wuppertal", "Bielefeld", "Bonn", "Münster",
    "Karlsruhe", "Mannheim", "Augsburg", "Wiesbaden", "Gelsenkirchen",
    "Mönchengladbach", "Braunschweig", "Chemnitz", "Kiel", "Aachen"
]

# Common job categories for keyword-based search
JOB_KEYWORDS = [
    "Software", "Engineer", "Developer", "Manager", "Analyst",
    "Marketing", "Sales", "Designer", "Consultant", "Administrator",
    "Techniker", "Ingenieur", "Entwickler", "Projektmanager",
    "Data Science", "Machine Learning", "Cloud", "DevOps",
    "Frontend", "Backend", "Full Stack", "Mobile", "Database",
    "Verkauf", "Vertrieb", "Kundenservice", "Logistik", "Produktion"
]

# Professional fields for broader search
PROFESSIONAL_FIELDS = [
    "Informatik", "IT", "Ingenieurwesen", "Betriebswirtschaft",
    "Marketing", "Vertrieb", "Gesundheit", "Bildung", "Forschung",
    "Finanzen", "Recht", "Medien", "Design", "Architektur"
]


class ArbeitsagenturMassLoader:
    """Mass loader for Bundesagentur für Arbeit jobs"""
    
    def __init__(self, db: PostgreSQLDatabase):
        """
        Initialize mass loader
        
        Args:
            db: Database connection instance
        """
        self.collector = ArbeitsagenturCollector()
        self.db = db
        self.seen_job_ids: Set[str] = set()
        self.stats = {
            'total_fetched': 0,
            'total_saved': 0,
            'duplicates': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def load_by_locations(self, cities: List[str], max_jobs: int = 1000) -> int:
        """
        Load jobs by searching major German cities
        
        Args:
            cities: List of city names to search
            max_jobs: Maximum total jobs to load
        
        Returns:
            Number of jobs successfully saved
        """
        logger.info(f"Starting location-based mass load for {len(cities)} cities")
        logger.info(f"Target: {max_jobs} jobs")
        
        jobs_per_city = max(10, max_jobs // len(cities))
        total_saved = 0
        
        for i, city in enumerate(cities, 1):
            if total_saved >= max_jobs:
                logger.info(f"Reached target of {max_jobs} jobs, stopping")
                break
            
            logger.info(f"[{i}/{len(cities)}] Searching {city}...")
            
            try:
                # Search with various filters to get diverse results
                for work_time in [None, self.collector.WORK_TIME_FULLTIME, self.collector.WORK_TIME_REMOTE]:
                    jobs = self.collector.search_and_parse(
                        location=city,
                        radius_km=50,
                        work_time=work_time,
                        max_results=jobs_per_city // 3,
                        days_since_posted=30  # Recent jobs only
                    )
                    
                    saved = self._save_jobs(jobs)
                    total_saved += saved
                    
                    if total_saved >= max_jobs:
                        break
                    
                    time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing {city}: {e}")
                self.stats['errors'] += 1
                continue
        
        return total_saved
    
    def load_by_keywords(self, keywords: List[str], max_jobs: int = 1000) -> int:
        """
        Load jobs by searching with job keywords
        
        Args:
            keywords: List of job search keywords
            max_jobs: Maximum total jobs to load
        
        Returns:
            Number of jobs successfully saved
        """
        logger.info(f"Starting keyword-based mass load with {len(keywords)} keywords")
        logger.info(f"Target: {max_jobs} jobs")
        
        jobs_per_keyword = max(10, max_jobs // len(keywords))
        total_saved = 0
        
        for i, keyword in enumerate(keywords, 1):
            if total_saved >= max_jobs:
                logger.info(f"Reached target of {max_jobs} jobs, stopping")
                break
            
            logger.info(f"[{i}/{len(keywords)}] Searching '{keyword}'...")
            
            try:
                jobs = self.collector.search_and_parse(
                    keywords=keyword,
                    max_results=jobs_per_keyword,
                    days_since_posted=30
                )
                
                saved = self._save_jobs(jobs)
                total_saved += saved
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing '{keyword}': {e}")
                self.stats['errors'] += 1
                continue
        
        return total_saved
    
    def load_by_fields(self, fields: List[str], max_jobs: int = 1000) -> int:
        """
        Load jobs by searching professional fields
        
        Args:
            fields: List of professional fields (berufsfeld)
            max_jobs: Maximum total jobs to load
        
        Returns:
            Number of jobs successfully saved
        """
        logger.info(f"Starting field-based mass load with {len(fields)} professional fields")
        logger.info(f"Target: {max_jobs} jobs")
        
        jobs_per_field = max(20, max_jobs // len(fields))
        total_saved = 0
        
        for i, field in enumerate(fields, 1):
            if total_saved >= max_jobs:
                logger.info(f"Reached target of {max_jobs} jobs, stopping")
                break
            
            logger.info(f"[{i}/{len(fields)}] Searching field '{field}'...")
            
            try:
                jobs = self.collector.search_and_parse(
                    berufsfeld=field,  # Use berufsfeld parameter
                    max_results=jobs_per_field,
                    days_since_posted=30
                )
                
                saved = self._save_jobs(jobs)
                total_saved += saved
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing field '{field}': {e}")
                self.stats['errors'] += 1
                continue
        
        return total_saved
    
    def load_comprehensive(self, max_jobs: int = 5000) -> int:
        """
        Comprehensive load combining all strategies
        
        Args:
            max_jobs: Maximum total jobs to load
        
        Returns:
            Number of jobs successfully saved
        """
        logger.info(f"Starting COMPREHENSIVE mass load")
        logger.info(f"Target: {max_jobs} jobs")
        logger.info("Strategy: Combining locations + keywords + fields")
        
        total_saved = 0
        
        # Strategy 1: Recent jobs across all major cities (40% of target)
        logger.info("\n=== Phase 1: Location-based search ===")
        strategy_1_target = int(max_jobs * 0.4)
        saved_1 = self.load_by_locations(MAJOR_CITIES[:20], strategy_1_target)
        total_saved += saved_1
        logger.info(f"Phase 1 complete: {saved_1} jobs saved")
        
        if total_saved >= max_jobs:
            return total_saved
        
        # Strategy 2: Keyword-based search (40% of target)
        logger.info("\n=== Phase 2: Keyword-based search ===")
        strategy_2_target = int(max_jobs * 0.4)
        saved_2 = self.load_by_keywords(JOB_KEYWORDS[:30], strategy_2_target)
        total_saved += saved_2
        logger.info(f"Phase 2 complete: {saved_2} jobs saved")
        
        if total_saved >= max_jobs:
            return total_saved
        
        # Strategy 3: Professional fields (20% of target)
        logger.info("\n=== Phase 3: Professional field search ===")
        strategy_3_target = int(max_jobs * 0.2)
        saved_3 = self.load_by_fields(PROFESSIONAL_FIELDS, strategy_3_target)
        total_saved += saved_3
        logger.info(f"Phase 3 complete: {saved_3} jobs saved")
        
        return total_saved
    
    def _save_jobs(self, jobs: List[Dict]) -> int:
        """
        Save jobs to database with duplicate detection
        
        Args:
            jobs: List of standardized job dictionaries
        
        Returns:
            Number of jobs successfully saved
        """
        if not jobs:
            return 0
        
        saved_count = 0
        
        for job in jobs:
            job_id = job.get('job_id')
            
            # Skip if already seen in this session
            if job_id in self.seen_job_ids:
                self.stats['duplicates'] += 1
                continue
            
            try:
                # Check if job already exists in database
                existing = self.db.get_job_by_id(job_id)
                if existing:
                    self.stats['duplicates'] += 1
                    self.seen_job_ids.add(job_id)
                    continue
                
                # Save new job
                self.db.add_job(job)
                saved_count += 1
                self.seen_job_ids.add(job_id)
                self.stats['total_saved'] += 1
                
            except Exception as e:
                logger.error(f"Error saving job {job_id}: {e}")
                self.stats['errors'] += 1
        
        self.stats['total_fetched'] += len(jobs)
        
        logger.info(f"Saved {saved_count}/{len(jobs)} jobs (duplicates: {len(jobs) - saved_count})")
        return saved_count
    
    def print_summary(self):
        """Print summary statistics"""
        duration = datetime.now() - self.stats['start_time']
        
        print("\n" + "="*70)
        print("MASS LOAD SUMMARY")
        print("="*70)
        print(f"Duration: {duration}")
        print(f"Total fetched: {self.stats['total_fetched']}")
        print(f"Total saved: {self.stats['total_saved']}")
        print(f"Duplicates skipped: {self.stats['duplicates']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Success rate: {self.stats['total_saved'] / max(1, self.stats['total_fetched']) * 100:.1f}%")
        print("="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Mass load jobs from Bundesagentur für Arbeit"
    )
    parser.add_argument(
        '--strategy',
        choices=['locations', 'keywords', 'fields', 'comprehensive'],
        default='comprehensive',
        help='Loading strategy to use'
    )
    parser.add_argument(
        '--max-jobs',
        type=int,
        default=1000,
        help='Maximum number of jobs to load'
    )
    parser.add_argument(
        '--cities',
        help='Comma-separated list of cities (for locations strategy)'
    )
    parser.add_argument(
        '--keywords',
        help='Comma-separated list of keywords (for keywords strategy)'
    )
    parser.add_argument(
        '--fields',
        help='Comma-separated list of professional fields (for fields strategy)'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    logger.info("Connecting to database...")
    db = PostgreSQLDatabase()
    
    # Initialize mass loader
    loader = ArbeitsagenturMassLoader(db)
    
    # Execute selected strategy
    try:
        if args.strategy == 'locations':
            cities = args.cities.split(',') if args.cities else MAJOR_CITIES
            loader.load_by_locations(cities, args.max_jobs)
        
        elif args.strategy == 'keywords':
            keywords = args.keywords.split(',') if args.keywords else JOB_KEYWORDS
            loader.load_by_keywords(keywords, args.max_jobs)
        
        elif args.strategy == 'fields':
            fields = args.fields.split(',') if args.fields else PROFESSIONAL_FIELDS
            loader.load_by_fields(fields, args.max_jobs)
        
        elif args.strategy == 'comprehensive':
            loader.load_comprehensive(args.max_jobs)
    
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    
    finally:
        # Print summary
        loader.print_summary()
        
        # Close database
        db.close()


if __name__ == "__main__":
    main()
