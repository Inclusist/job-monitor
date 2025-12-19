"""
Bundesagentur für Arbeit (German Federal Employment Agency) Job Collector

This collector interfaces with the official German government job search API (JOBSUCHE).
No registration or API key required - publicly accessible.

API Documentation: https://jobsuche.api.bund.de/
Base URL: https://rest.arbeitsagentur.de/jobboerse/jobsuche-service
"""

import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ArbeitsagenturCollector:
    """
    Collector for German Federal Employment Agency JOBSUCHE API
    
    Features:
    - Public API (no registration required)
    - Comprehensive German job market coverage
    - Official government source
    - Free unlimited access
    """
    
    BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
    API_KEY = "jobboerse-jobsuche"  # Public API key for all users
    
    # Job type constants
    JOB_TYPE_EMPLOYMENT = 1
    JOB_TYPE_SELF_EMPLOYMENT = 2
    JOB_TYPE_TRAINING = 4
    JOB_TYPE_INTERNSHIP = 34
    
    # Work time constants
    WORK_TIME_FULLTIME = "vz"
    WORK_TIME_PARTTIME = "tz"
    WORK_TIME_REMOTE = "ho"
    WORK_TIME_SHIFT = "snw"
    WORK_TIME_WEEKEND = "woe"
    WORK_TIME_HOME_OFFICE = "ho"
    
    def __init__(self):
        """Initialize the collector with session and headers"""
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.API_KEY,
            'User-Agent': 'JobMonitor/1.0',
            'Accept': 'application/json'
        })
        
    def search_jobs(self,
                   keywords: Optional[str] = None,
                   location: Optional[str] = None,
                   radius_km: int = 50,
                   job_type: int = JOB_TYPE_EMPLOYMENT,
                   work_time: Optional[str] = None,
                   days_since_posted: Optional[int] = None,
                   page: int = 1,
                   page_size: int = 100,
                   **kwargs) -> Dict:
        """
        Search for jobs using the German Federal Employment Agency API
        
        Args:
            keywords: Job title or search terms (e.g., "Python Developer")
            location: City, region, or postal code in Germany (e.g., "Berlin", "10115")
            radius_km: Search radius in kilometers (0-200, default: 50)
            job_type: Type of job offering:
                1 = Employment (Arbeit)
                2 = Self-employment (Selbstständigkeit)
                4 = Training/Apprenticeship (Ausbildung)
                34 = Internship (Praktikum/Trainee)
            work_time: Work time type:
                "vz" = Full-time (Vollzeit)
                "tz" = Part-time (Teilzeit)
                "ho" = Home office/Remote
                "snw" = Shift work (Schicht/Nacht/Wochenende)
                "woe" = Weekend work
            days_since_posted: Jobs posted within last N days (0-100)
            page: Page number for pagination (starts at 1)
            page_size: Results per page (max 100)
            **kwargs: Additional API parameters
        
        Returns:
            Dictionary containing:
                - stellenangebote: List of job offers
                - maxErgebnisse: Total number of results
                - page: Current page number
                - size: Page size
                - success: Whether request succeeded
        
        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        endpoint = f"{self.BASE_URL}/pc/v4/jobs"
        
        params = {
            'page': max(page, 1),  # Pages start at 1, not 0
            'size': min(page_size, 100),  # Max 100 per request
            'angebotsart': job_type
        }
        
        # Add optional parameters
        if keywords:
            params['was'] = keywords
        
        if location:
            params['wo'] = location
            params['umkreis'] = min(radius_km, 200)  # Max 200 km
        
        if work_time:
            params['arbeitszeit'] = work_time
        
        if days_since_posted is not None:
            params['veroeffentlichtseit'] = min(days_since_posted, 100)
        
        # Add any extra parameters
        params.update(kwargs)
        
        try:
            logger.info(f"Searching Arbeitsagentur jobs: keywords='{keywords}', location='{location}'")
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            data['success'] = True
            
            job_count = len(data.get('stellenangebote', []))
            total_count = data.get('maxErgebnisse', 0)
            logger.info(f"Retrieved {job_count} jobs from Arbeitsagentur (total: {total_count})")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from Arbeitsagentur: {e}")
            return {
                'stellenangebote': [],
                'maxErgebnisse': 0,
                'success': False,
                'error': str(e)
            }
    
    def get_all_jobs(self,
                    keywords: Optional[str] = None,
                    location: Optional[str] = None,
                    max_results: int = 1000,
                    **kwargs) -> List[Dict]:
        """
        Fetch all matching jobs across multiple pages
        
        Args:
            keywords: Job search terms
            location: Location to search in
            max_results: Maximum number of jobs to retrieve
            **kwargs: Additional search parameters
        
        Returns:
            List of all job dictionaries
        """
        all_jobs = []
        page = 1  # Pages start at 1
        page_size = 100
        
        while len(all_jobs) < max_results:
            result = self.search_jobs(
                keywords=keywords,
                location=location,
                page=page,
                page_size=page_size,
                **kwargs
            )
            
            if not result.get('success'):
                logger.warning(f"Failed to fetch page {page}, stopping pagination")
                break
            
            jobs = result.get('stellenangebote', [])
            if not jobs:
                break  # No more results
            
            all_jobs.extend(jobs)
            
            # Check if we've reached the end
            total_available = result.get('maxErgebnisse', 0)
            if len(all_jobs) >= total_available or len(all_jobs) >= max_results:
                break
            
            page += 1
        
        logger.info(f"Retrieved total of {len(all_jobs)} jobs from Arbeitsagentur")
        return all_jobs[:max_results]
    
    def parse_job(self, job_data: Dict) -> Dict:
        """
        Parse a job from Arbeitsagentur API format to our standard format
        
        Args:
            job_data: Raw job data from API
        
        Returns:
            Standardized job dictionary matching our database schema
        """
        try:
            # Extract basic info - use refnr as job ID since hashId not always present
            job_id = job_data.get('hashId', job_data.get('refnr', ''))
            title = job_data.get('titel', 'No title')
            
            # Company info
            arbeitgeber = job_data.get('arbeitgeber', 'Unknown')
            
            # Location
            arbeitsort = job_data.get('arbeitsort', {})
            location = arbeitsort.get('ort', '')
            plz = arbeitsort.get('plz', '')
            region = arbeitsort.get('region', '')
            
            if plz and location:
                location_str = f"{plz} {location}"
            elif location:
                location_str = location
            elif region:
                location_str = region
            else:
                location_str = "Germany"
            
            # Description - combine beruf (occupation) with title for better context
            beruf = job_data.get('beruf', '')
            description = f"{beruf}\n\n{title}" if beruf else title
            
            # External URL if available, otherwise use job detail page
            external_url = job_data.get('externeUrl', '')
            if not external_url and job_id:
                external_url = f"https://www.arbeitsagentur.de/jobsuche/jobdetails/{job_id}"
            
            # Employment type and work time
            angebotsart = job_data.get('angebotsart', '')
            arbeitszeit = job_data.get('arbeitszeitModelle', [])
            
            # Salary - not always available
            gehalt_info = ""
            
            # Source and posted date
            eintrittsdatum = job_data.get('eintrittsdatum', '')
            aktuelleVeroeffentlichungsdatum = job_data.get('aktuelleVeroeffentlichungsdatum', '')
            
            # Parse date - handle dates without time component
            date_posted = None
            if aktuelleVeroeffentlichungsdatum:
                try:
                    # Try with time component first
                    date_posted = datetime.fromisoformat(aktuelleVeroeffentlichungsdatum.replace('Z', '+00:00'))
                except:
                    try:
                        # Try date only format (YYYY-MM-DD)
                        date_posted = datetime.strptime(aktuelleVeroeffentlichungsdatum, '%Y-%m-%d')
                    except:
                        pass
            
            # Build standardized job dictionary
            standardized = {
                'job_id': f"arbeitsagentur_{job_id}",
                'title': title,
                'company': arbeitgeber,
                'location': location_str,
                'description': description,
                'salary': gehalt_info,
                'source': 'Arbeitsagentur',
                'url': external_url,
                'date_posted': date_posted.isoformat() if date_posted else datetime.now().isoformat(),
                'employment_type': angebotsart,
                'work_time': ', '.join(arbeitszeit) if arbeitszeit else '',
                'raw_data': job_data  # Store original for reference
            }
            
            return standardized
            
        except Exception as e:
            logger.error(f"Error parsing Arbeitsagentur job: {e}")
            return None
    
    def search_and_parse(self,
                        keywords: Optional[str] = None,
                        location: Optional[str] = None,
                        max_results: int = 1000,
                        **kwargs) -> List[Dict]:
        """
        Search for jobs and return them in standardized format
        
        Args:
            keywords: Job search terms
            location: Location to search in
            max_results: Maximum number of jobs to retrieve
            **kwargs: Additional search parameters
        
        Returns:
            List of standardized job dictionaries ready for database insertion
        """
        raw_jobs = self.get_all_jobs(
            keywords=keywords,
            location=location,
            max_results=max_results,
            **kwargs
        )
        
        standardized_jobs = []
        for job in raw_jobs:
            parsed = self.parse_job(job)
            if parsed:
                standardized_jobs.append(parsed)
        
        logger.info(f"Parsed {len(standardized_jobs)} jobs from Arbeitsagentur")
        return standardized_jobs


def main():
    """Example usage of the Arbeitsagentur collector"""
    collector = ArbeitsagenturCollector()
    
    # Example 1: Search for Python developers in Berlin
    print("\n=== Searching for Python developers in Berlin ===")
    jobs = collector.search_and_parse(
        keywords="Python Developer",
        location="Berlin",
        radius_km=50,
        work_time=ArbeitsagenturCollector.WORK_TIME_FULLTIME,
        max_results=10
    )
    
    for i, job in enumerate(jobs[:5], 1):
        print(f"\n{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   URL: {job['url']}")
    
    # Example 2: Search for Data Science jobs in Munich
    print("\n\n=== Searching for Data Science jobs in Munich ===")
    result = collector.search_jobs(
        keywords="Data Science",
        location="München",
        radius_km=30,
        page_size=5
    )
    
    if result.get('success'):
        print(f"Total results: {result.get('maxErgebnisse', 0)}")
        for job in result.get('stellenangebote', [])[:3]:
            print(f"\n- {job.get('titel', 'No title')}")
            print(f"  Company: {job.get('arbeitgeber', 'N/A')}")
            arbeitsort = job.get('arbeitsort', {})
            print(f"  Location: {arbeitsort.get('ort', 'N/A')}")
    
    # Example 3: Get recent remote jobs
    print("\n\n=== Searching for recent remote jobs ===")
    jobs = collector.search_and_parse(
        keywords="Software",
        work_time=ArbeitsagenturCollector.WORK_TIME_HOME_OFFICE,
        days_since_posted=7,
        max_results=5
    )
    
    print(f"Found {len(jobs)} remote jobs posted in last 7 days")
    for job in jobs:
        print(f"\n- {job['title']} at {job['company']}")
        print(f"  {job['location']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
