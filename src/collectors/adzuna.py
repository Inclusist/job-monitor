"""
Adzuna API Collector
Collects jobs from Adzuna job search engine
Free tier: 250 calls/month with no rate limit
Supports multiple countries including Germany
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
from .source_filter import SourceFilter


class AdzunaCollector:
    """Collects jobs using Adzuna API"""
    
    # Country mappings
    COUNTRY_CODES = {
        'de': 'de',
        'germany': 'de',
        'us': 'us',
        'usa': 'us',
        'uk': 'gb',
        'gb': 'gb',
        'france': 'fr',
        'fr': 'fr',
    }
    
    def __init__(self, app_id: str, app_key: str, enable_filtering: bool = True, min_quality: int = 2):
        """
        Initialize Adzuna collector
        
        Args:
            app_id: Adzuna Application ID
            app_key: Adzuna Application Key
            enable_filtering: Whether to filter out low-quality sources
            min_quality: Minimum quality score (1=all, 2=remove spam, 3=only trusted)
        """
        self.app_id = app_id
        self.app_key = app_key
        self.base_url = "https://api.adzuna.com/v1/api/jobs"
        self.enable_filtering = enable_filtering
        self.min_quality = min_quality
        self.source_filter = SourceFilter() if enable_filtering else None
    
    def search_jobs(
        self,
        query: str,
        location: str = None,
        num_pages: int = 1,
        results_per_page: int = 10,
        country: str = 'de',
        max_days_old: int = 7,
        sort_by: str = 'date'  # date, relevance, salary
    ) -> List[Dict]:
        """
        Search for jobs using Adzuna API
        
        Args:
            query: Job title or keywords
            location: Location (city or region)
            num_pages: Number of pages to fetch
            results_per_page: Results per page (max 50)
            country: Country code (de, us, gb, etc.)
            max_days_old: Only return jobs posted in last N days
            sort_by: Sort order (date, relevance, salary)
            
        Returns:
            List of job dictionaries
        """
        # Normalize country code
        country = self.COUNTRY_CODES.get(country.lower(), country.lower())
        
        all_jobs = []
        
        for page in range(1, num_pages + 1):
            endpoint = f"{self.base_url}/{country}/search/{page}"
            
            params = {
                'app_id': self.app_id,
                'app_key': self.app_key,
                'what': query,
                'results_per_page': min(results_per_page, 50),  # Max 50
                'sort_by': sort_by,
                'max_days_old': max_days_old
            }
            
            # Clean location for better matching
            if location:
                # Remove country names since we're already filtering by country in URL
                clean_location = location.replace(', Germany', '').replace(', Deutschland', '').strip()
                if clean_location.lower() != 'remote':  # Don't pass 'Remote' as location
                    params['where'] = clean_location
            
            try:
                response = requests.get(endpoint, params=params)
                
                print(f"Adzuna API request: {endpoint}")
                print(f"Params: {params}")
                print(f"Response status: {response.status_code}")
                
                # Check for quota/rate limit errors
                if response.status_code == 429:
                    print("Adzuna API: Rate limit exceeded")
                    break
                elif response.status_code == 403:
                    print("Adzuna API: Monthly quota exceeded (250 calls/month)")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                print(f"Response data keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
                
                results = data.get('results', [])
                print(f"Number of results: {len(results)}")
                
                if not results:
                    print(f"No results found. Full response: {data}")
                    break  # No more results
                
                for job in results:
                    all_jobs.append(self._parse_job(job))
                
                print(f"Adzuna page {page}: Found {len(results)} jobs")
                
                # If we got fewer results than requested, we've reached the end
                if len(results) < results_per_page:
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"Error fetching jobs from Adzuna: {e}")
                print(f"Response text: {e.response.text if hasattr(e, 'response') and e.response else 'No response'}")
                break
        
        # Apply source filtering if enabled
        if self.enable_filtering and self.source_filter and all_jobs:
            print(f"\nApplying source quality filter (min_quality={self.min_quality})...")
            all_jobs = self.source_filter.filter_jobs(all_jobs, min_quality=self.min_quality)
        
        return all_jobs
    
    def _parse_job(self, job_data: Dict) -> Dict:
        """Parse Adzuna job data into standardized format"""
        
        # Format salary
        salary = None
        salary_min = job_data.get('salary_min')
        salary_max = job_data.get('salary_max')
        
        if salary_min and salary_max:
            salary = f"€{salary_min:,.0f} - €{salary_max:,.0f}"
        elif salary_min:
            salary = f"€{salary_min:,.0f}+"
        elif salary_max:
            salary = f"Up to €{salary_max:,.0f}"
        
        # Format location
        location_parts = []
        if job_data.get('location', {}).get('display_name'):
            location_parts.append(job_data['location']['display_name'])
        location = ', '.join(location_parts) if location_parts else "Remote"
        
        # Format posted date
        posted_date = job_data.get('created')
        
        return {
            "title": job_data.get('title', ''),
            "company": job_data.get('company', {}).get('display_name', 'Unknown'),
            "location": location,
            "description": job_data.get('description', ''),
            "url": job_data.get('redirect_url', ''),
            "salary": salary,
            "employment_type": job_data.get('contract_type', ''),
            "posted_date": posted_date,
            "source": "Adzuna",
            "external_id": job_data.get('id', ''),
            # Additional metadata
            "category": job_data.get('category', {}).get('label', ''),
            "contract_time": job_data.get('contract_time', ''),  # full_time, part_time
        }
