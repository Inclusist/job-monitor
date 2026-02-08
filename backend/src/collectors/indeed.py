"""
Indeed API integration for job search
Uses Indeed Publisher API to search for jobs
"""

import requests
import time
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode


class IndeedCollector:
    """Collect jobs from Indeed Publisher API"""
    
    BASE_URL = "http://api.indeed.com/ads/apisearch"
    
    def __init__(self, publisher_id: str):
        """
        Initialize Indeed collector
        
        Args:
            publisher_id: Your Indeed Publisher ID
        """
        self.publisher_id = publisher_id
    
    def search(
        self,
        query: str,
        location: str = "Germany",
        radius: int = 50,
        days_back: int = 1,
        limit: int = 25,
        sort: str = "date"
    ) -> List[Dict[str, Any]]:
        """
        Search for jobs on Indeed
        
        Args:
            query: Search keywords
            location: Job location
            radius: Search radius in km
            days_back: Only jobs from last N days
            limit: Max results to return
            sort: Sort by 'relevance' or 'date'
            
        Returns:
            List of job dictionaries
        """
        params = {
            'publisher': self.publisher_id,
            'q': query,
            'l': location,
            'radius': radius,
            'fromage': days_back,
            'limit': limit,
            'sort': sort,
            'format': 'json',
            'v': '2',
            'userip': '1.2.3.4',  # Required by API
            'useragent': 'Mozilla/5.0'  # Required by API
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'results' in data:
                return self._parse_results(data['results'], query, location)
            else:
                print(f"No results found for query: {query} in {location}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching from Indeed: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
    
    def search_multiple(
        self,
        queries: List[str],
        locations: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for multiple query/location combinations
        
        Args:
            queries: List of search keywords
            locations: List of locations
            **kwargs: Additional parameters for search()
            
        Returns:
            Combined list of job dictionaries (deduplicated)
        """
        all_jobs = []
        seen_job_keys = set()
        
        total_searches = len(queries) * len(locations)
        search_count = 0
        
        for query in queries:
            for location in locations:
                search_count += 1
                print(f"[{search_count}/{total_searches}] Searching Indeed: '{query}' in '{location}'")
                
                jobs = self.search(query, location, **kwargs)
                
                # Deduplicate based on job_key
                for job in jobs:
                    job_key = job.get('job_id')
                    if job_key and job_key not in seen_job_keys:
                        seen_job_keys.add(job_key)
                        all_jobs.append(job)
                
                # Rate limiting - be nice to Indeed's API
                time.sleep(1)
        
        print(f"Indeed search complete. Found {len(all_jobs)} unique jobs.")
        return all_jobs
    
    def _parse_results(
        self,
        results: List[Dict],
        query: str,
        location: str
    ) -> List[Dict[str, Any]]:
        """Parse Indeed API results into standardized format"""
        jobs = []
        
        for result in results:
            # Create unique job ID
            job_key = result.get('jobkey', '')
            job_id = f"indeed_{job_key}"
            
            # Extract and clean data
            job = {
                'job_id': job_id,
                'source': 'indeed',
                'title': result.get('jobtitle', ''),
                'company': result.get('company', ''),
                'location': result.get('formattedLocation', result.get('city', location)),
                'description': self._clean_description(result.get('snippet', '')),
                'url': result.get('url', ''),
                'posted_date': result.get('date', ''),
                'salary': result.get('formattedRelativeTime', ''),
                'search_query': query,
                'search_location': location
            }
            
            jobs.append(job)
        
        return jobs
    
    def _clean_description(self, description: str) -> str:
        """Clean up job description (remove HTML, etc.)"""
        # Indeed's snippet sometimes has HTML tags
        import re
        description = re.sub(r'<[^>]+>', '', description)
        description = description.replace('&nbsp;', ' ')
        description = description.replace('&amp;', '&')
        return description.strip()
    
    def get_full_description(self, job_url: str) -> Optional[str]:
        """
        Fetch full job description from Indeed job page
        Note: This requires web scraping, not part of official API
        """
        # TODO: Implement if needed
        # For now, we'll work with snippets from API
        pass


def test_indeed():
    """Test function"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    publisher_id = os.getenv('INDEED_PUBLISHER_ID')
    if not publisher_id or publisher_id == 'your_publisher_id_here':
        print("Error: INDEED_PUBLISHER_ID not set in .env file")
        print("Please sign up at https://www.indeed.com/publisher")
        return
    
    collector = IndeedCollector(publisher_id)
    
    # Test single search
    print("Testing Indeed API...")
    jobs = collector.search(
        query="Data Science Lead",
        location="Berlin, Germany",
        days_back=7
    )
    
    print(f"\nFound {len(jobs)} jobs")
    
    if jobs:
        print("\nFirst job:")
        job = jobs[0]
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Posted: {job['posted_date']}")
        print(f"URL: {job['url']}")


if __name__ == "__main__":
    test_indeed()
