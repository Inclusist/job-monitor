"""
Active Jobs DB API Collector (RapidAPI)
Collects jobs from ATS platforms and career sites
Free Basic Plan: 5000 jobs/month, 200 requests/month, 1000 requests/hour
Germany coverage: 40k-50k jobs
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .source_filter import SourceFilter


class ActiveJobsCollector:
    """Collects jobs using Active Jobs DB API on RapidAPI"""
    
    def __init__(self, api_key: str, enable_filtering: bool = True, min_quality: int = 2):
        """
        Initialize Active Jobs DB collector
        
        Args:
            api_key: RapidAPI key for Active Jobs DB
            enable_filtering: Whether to filter out low-quality sources
            min_quality: Minimum quality score (1=all, 2=remove spam, 3=only trusted)
        """
        self.api_key = api_key
        self.base_url = "https://active-jobs-db.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "active-jobs-db.p.rapidapi.com"
        }
        self.enable_filtering = enable_filtering
        self.min_quality = min_quality
        self.source_filter = SourceFilter() if enable_filtering else None
    
    def search_all_recent_jobs(
        self,
        location: str = "Germany",
        max_pages: int = 10,
        date_posted: str = "24h",
        remote_only: bool = False,
        ai_work_arrangement: str = None,
        ai_employment_type: str = None,
        ai_seniority: str = None,
        ai_industry: str = None
    ) -> List[Dict]:
        """
        Fetch all recent jobs from a country without keyword filtering
        More efficient than multiple keyword searches

        Args:
            location: Country or region
            max_pages: Maximum pages to fetch (100 jobs per page)
            date_posted: '24h' or 'week'
            remote_only: Only return remote jobs
            ai_work_arrangement: AI filter for work arrangement (remote, hybrid, onsite)
            ai_employment_type: AI filter for employment type (full-time, part-time, contract)
            ai_seniority: AI filter for seniority level (entry, mid, senior, lead)
            ai_industry: AI filter for industry

        Returns:
            List of all job dictionaries
        """
        # Choose endpoint
        if date_posted == "24h":
            endpoint = f"{self.base_url}/active-ats-24h"
        else:
            endpoint = f"{self.base_url}/active-ats-7d"
        
        all_jobs = []
        
        for page_num in range(max_pages):
            offset = page_num * 100
            
            params = {
                'limit': 100,
                'offset': offset,
                'description_type': 'text',
                'include_ai': 'true'  # Always include AI metadata
            }

            # Add location filter if provided
            if location:
                params['location_filter'] = location

            # Add remote filter if requested
            if remote_only:
                params['remote'] = 'true'

            # API-level AI filters
            if ai_work_arrangement:
                params['ai_work_arrangement_filter'] = ai_work_arrangement

            if ai_employment_type:
                params['ai_employment_type_filter'] = ai_employment_type

            if ai_seniority:
                params['ai_seniority_filter'] = ai_seniority

            if ai_industry:
                params['ai_industry_filter'] = ai_industry

            try:
                response = requests.get(endpoint, headers=self.headers, params=params)
                
                print(f"Active Jobs DB bulk fetch page {page_num + 1}...")
                print(f"  Response status: {response.status_code}")
                
                if response.status_code == 429:
                    jobs_remaining = response.headers.get('x-ratelimit-jobs-remaining')
                    requests_remaining = response.headers.get('x-ratelimit-requests-remaining')
                    print(f"  Rate limit hit - Jobs: {jobs_remaining}, Requests: {requests_remaining}")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list):
                    jobs_data = data
                else:
                    jobs_data = data.get('data', [])
                
                if not jobs_data:
                    print(f"  No more results on page {page_num + 1}")
                    break
                
                for job in jobs_data:
                    all_jobs.append(self._parse_job(job))
                
                print(f"  Found {len(jobs_data)} jobs (total so far: {len(all_jobs)})")
                
                # Check headers
                jobs_remaining = response.headers.get('x-ratelimit-jobs-remaining')
                requests_remaining = response.headers.get('x-ratelimit-requests-remaining')
                if jobs_remaining:
                    print(f"  Quota remaining - Jobs: {jobs_remaining}, Requests: {requests_remaining}")
                
                # If we got fewer results than requested, we've reached the end
                if len(jobs_data) < 100:
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"Error fetching jobs from Active Jobs DB: {e}")
                break
        
        return all_jobs
    
    def search_jobs(
        self,
        query: str,
        location: str = None,
        num_pages: int = 1,
        results_per_page: int = 10,
        date_posted: str = "week",  # week, 24h, 1h (1h requires Ultra plan)
        description_type: str = None,  # 'text' or 'html'
        remote_only: bool = False,
        ai_work_arrangement: str = None,  # Filter: remote, hybrid, onsite
        ai_employment_type: str = None,   # Filter: full-time, part-time, contract
        ai_seniority: str = None,         # Filter: entry, mid, senior, lead
        ai_industry: str = None           # Filter: technology, finance, healthcare, etc.
    ) -> List[Dict]:
        """
        Search for jobs using Active Jobs DB API with AI-powered filters

        Args:
            query: Job title or keywords
            location: Location (e.g., "Germany", "Berlin")
            num_pages: Number of pages to fetch
            results_per_page: Results per page (max 100)
            date_posted: Filter by date (week=7 days, 24h=24 hours)
            description_type: Include description ('text' or 'html')
            remote_only: Only return remote jobs
            ai_work_arrangement: AI filter for work arrangement (remote, hybrid, onsite)
            ai_employment_type: AI filter for employment type (full-time, part-time, contract)
            ai_seniority: AI filter for seniority level (entry, mid, senior, lead)
            ai_industry: AI filter for industry (technology, finance, healthcare, etc.)

        Returns:
            List of job dictionaries
        """
        # Choose endpoint based on date_posted
        if date_posted == "24h":
            endpoint = f"{self.base_url}/active-ats-24h"
        else:
            endpoint = f"{self.base_url}/active-ats-7d"  # Default to 7 days
        
        all_jobs = []
        
        for page_num in range(num_pages):
            offset = page_num * results_per_page

            params = {
                'limit': min(results_per_page, 100),  # Max 100 per request
                'offset': offset
            }

            # Add title filter using advanced_title_filter (required for proper API results)
            # Format: 'query' with single quotes for proper parsing
            if query:
                params['advanced_title_filter'] = f"'{query}'"
            
            # Add location filter
            if location:
                params['location_filter'] = location
            
            # Add remote filter
            if remote_only:
                params['remote'] = 'true'

            # Include job descriptions if requested
            if description_type in ['text', 'html']:
                params['description_type'] = description_type

            # Include AI-extracted metadata (employment type, work arrangement, etc.)
            params['include_ai'] = 'true'

            # API-level AI filters (more efficient than local filtering)
            if ai_work_arrangement:
                params['ai_work_arrangement_filter'] = ai_work_arrangement

            if ai_employment_type:
                params['ai_employment_type_filter'] = ai_employment_type

            if ai_seniority:
                params['ai_seniority_filter'] = ai_seniority

            if ai_industry:
                params['ai_industry_filter'] = ai_industry

            try:
                response = requests.get(endpoint, headers=self.headers, params=params)
                
                # Check for quota/rate limit errors
                if response.status_code == 429:
                    # Check headers for details
                    rate_limit_reset = response.headers.get('x-ratelimit-requests-reset')
                    jobs_remaining = response.headers.get('x-ratelimit-jobs-remaining')
                    requests_remaining = response.headers.get('x-ratelimit-requests-remaining')
                    
                    print(f"Active Jobs DB: Rate limit exceeded (429)")
                    print(f"  Jobs remaining: {jobs_remaining}")
                    print(f"  Requests remaining: {requests_remaining}")
                    print(f"  Reset in: {rate_limit_reset} seconds" if rate_limit_reset else "  Reset time: unknown")
                    
                    try:
                        error_data = response.json()
                        print(f"  Error response: {error_data}")
                    except:
                        print(f"  Response text: {response.text}")
                    
                    if jobs_remaining == '0':
                        print("  Issue: Monthly JOB quota exhausted (5000 jobs/month)")
                    elif requests_remaining == '0':
                        print("  Issue: Monthly REQUEST quota exhausted (200 requests/month)")
                    else:
                        print("  Issue: Hourly rate limit (1000 requests/hour)")
                    break
                elif response.status_code == 403:
                    error_msg = "Monthly quota exceeded"
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            error_msg = error_data['message']
                    except:
                        pass
                    print(f"Active Jobs DB: {error_msg}")
                    print("Basic plan: 5000 jobs/month, 200 requests/month")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                # Extract jobs from response - API returns list directly
                if isinstance(data, list):
                    jobs_data = data
                else:
                    jobs_data = data.get('data', [])
                
                if not jobs_data:
                    break  # No more results
                
                # Check rate limit headers
                jobs_remaining = response.headers.get('x-ratelimit-jobs-remaining')
                requests_remaining = response.headers.get('x-ratelimit-requests-remaining')
                
                if jobs_remaining:
                    print(f"Active Jobs DB: {jobs_remaining} jobs remaining this month")
                
                for job in jobs_data:
                    all_jobs.append(self._parse_job(job))
                
                print(f"Active Jobs DB page {page_num + 1}: Found {len(jobs_data)} jobs")
                
                # If we got fewer results than requested, we've reached the end
                if len(jobs_data) < results_per_page:
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"Error fetching jobs from Active Jobs DB: {e}")
                break
        
        # Apply source filtering if enabled
        if self.enable_filtering and self.source_filter and all_jobs:
            print(f"\nApplying source quality filter (min_quality={self.min_quality})...")
            all_jobs = self.source_filter.filter_jobs(all_jobs, min_quality=self.min_quality)
        
        return all_jobs
    
    def _parse_job(self, job_data: Dict) -> Dict:
        """Parse Active Jobs DB job data into standardized format"""
        
        # Format salary from raw data
        salary = None
        salary_raw = job_data.get('salary_raw')
        if salary_raw and isinstance(salary_raw, dict):
            currency = salary_raw.get('currency', 'EUR')
            min_val = salary_raw.get('minValue')
            max_val = salary_raw.get('maxValue')
            value = salary_raw.get('value')
            unit = salary_raw.get('unitText', 'YEAR')
            
            # Ensure values are numbers, not dicts
            try:
                if min_val and max_val and isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                    salary = f"{currency} {int(min_val):,} - {int(max_val):,} per {unit.lower()}"
                elif value and isinstance(value, (int, float)):
                    salary = f"{currency} {int(value):,} per {unit.lower()}"
            except (ValueError, TypeError):
                pass  # Skip if salary values are malformed
        
        # Extract locations
        # locations_derived is a list of strings like ["Hamburg, Hamburg, Germany"]
        locations = job_data.get('locations_derived', [])
        if locations and isinstance(locations, list):
            # Join location strings, they already contain city, region, country
            location_str = ', '.join([loc for loc in locations if isinstance(loc, str)])
        else:
            location_str = ""
        
        # Get employment type
        employment_types = job_data.get('employment_type', [])
        employment_type = ', '.join(employment_types) if employment_types else ''
        
        # Format posted date
        posted_date = job_data.get('date_posted', '')

        # Extract AI-powered fields
        ai_employment_type = job_data.get('ai_employment_type_filter', '')
        ai_work_arrangement = job_data.get('ai_work_arrangement_filter', '')
        ai_seniority = job_data.get('ai_seniority_filter', '')
        ai_industry = job_data.get('ai_industry_filter', '')

        return {
            "title": job_data.get('title', ''),
            "company": job_data.get('organization', ''),
            "location": location_str,
            "description": job_data.get('description_text') or job_data.get('description_html', ''),
            "url": job_data.get('url', ''),
            "salary": salary,
            "employment_type": employment_type,
            "posted_date": posted_date,
            "source": f"Active Jobs DB ({job_data.get('source', 'ATS')})",
            "external_id": job_data.get('id', ''),
            # Additional metadata
            "organization_url": job_data.get('organization_url', ''),
            "organization_logo": job_data.get('organization_logo', ''),
            "remote": job_data.get('location_type') == 'TELECOMMUTE',
            # AI-extracted metadata for better matching
            "ai_employment_type": ai_employment_type,
            "ai_work_arrangement": ai_work_arrangement,
            "ai_seniority": ai_seniority,
            "ai_industry": ai_industry,
        }
