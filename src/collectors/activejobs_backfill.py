"""
Active Jobs DB Backfill Collector (RapidAPI)
Uses the 6-month backfill endpoint for initial user onboarding
Optimized for fetching historical data with pipe operators
"""

import requests
from typing import List, Dict, Optional


class ActiveJobsBackfillCollector:
    """Collector for 6-month backfill using Active Jobs DB API"""

    def __init__(self, api_key: str):
        """
        Initialize backfill collector

        Args:
            api_key: RapidAPI key for Active Jobs DB
        """
        self.api_key = api_key
        self.base_url = "https://active-jobs-db.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "active-jobs-db.p.rapidapi.com"
        }

    def search_backfill(
        self,
        query: str = None,
        location: str = None,
        limit: int = 500,
        offset: int = 0,
        description_type: str = "text",
        ai_work_arrangement: str = None,
        ai_employment_type: str = None,
        ai_experience_level: str = None,
        ai_taxonomy: str = None
    ) -> List[Dict]:
        """
        Fetch jobs from 6-month backfill endpoint

        Supports pipe operators for OR queries:
        - query: "Data Scientist|ML Engineer|AI Researcher"
        - location: "Berlin|Hamburg|Munich"

        Args:
            query: Job title or keywords (supports pipe operator: "title1|title2")
            location: Location filter (supports pipe operator: "city1|city2")
            limit: Maximum results to fetch (default: 500)
            offset: Offset for pagination (default: 0)
            description_type: Include description ('text' or 'html')
            ai_work_arrangement: AI filter for work arrangement (On-site, Hybrid, Remote OK, Remote Solely)
            ai_employment_type: AI filter for employment type (FULL_TIME, PART_TIME, CONTRACTOR, etc)
            ai_experience_level: AI filter for experience level (0-2, 2-5, 5-10, 10+)
            ai_taxonomy: AI filter for industry/taxonomy (Technology, Healthcare, etc)

        Returns:
            List of job dictionaries
        """
        # Using 6-month backfill endpoint for historical data
        endpoint = f"{self.base_url}/active-ats-6m"

        params = {
            'limit': min(limit, 1000),  # Max 1000 per request
            'offset': offset
        }

        # Add advanced title filter (supports pipe operator for multiple titles)
        if query:
            params['advanced_title_filter'] = query

        # Add location filter (supports pipe operator)
        if location:
            params['location_filter'] = location

        # Include job descriptions
        if description_type in ['text', 'html']:
            params['description_type'] = description_type

        # Include AI-extracted metadata
        params['include_ai'] = 'true'

        # API-level AI filters (using correct parameter names from API docs)
        if ai_work_arrangement:
            params['ai_work_arrangement_filter'] = ai_work_arrangement

        if ai_employment_type:
            params['ai_employment_type_filter'] = ai_employment_type

        if ai_experience_level:
            params['ai_experience_level_filter'] = ai_experience_level

        if ai_taxonomy:
            params['ai_taxonomies_a_filter'] = ai_taxonomy

        try:
            print(f"  DEBUG: Calling {endpoint}")
            print(f"  DEBUG: Params: {params}")

            response = requests.get(endpoint, headers=self.headers, params=params)

            print(f"  DEBUG: Response status: {response.status_code}")

            # Check for quota/rate limit errors
            if response.status_code == 429:
                error_msg = "Rate limit exceeded"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    pass
                print(f"❌ Active Jobs DB Backfill: {error_msg}")
                return []

            if response.status_code == 403:
                print("❌ Active Jobs DB Backfill: API key invalid or quota exceeded")
                try:
                    error_data = response.json()
                    print(f"  Error details: {error_data}")
                except:
                    pass
                return []

            if response.status_code != 200:
                print(f"❌ Active Jobs DB Backfill: HTTP {response.status_code}")
                try:
                    print(f"  Response: {response.text[:500]}")
                except:
                    pass
                return []

            response.raise_for_status()
            data = response.json()

            print(f"  DEBUG: Response type: {type(data)}, len: {len(data) if isinstance(data, list) else 'N/A'}")

            # Extract jobs from response
            if isinstance(data, list):
                jobs_data = data
            else:
                jobs_data = data.get('data', [])

            # Log quota remaining
            jobs_remaining = response.headers.get('x-ratelimit-jobs-remaining')
            requests_remaining = response.headers.get('x-ratelimit-requests-remaining')
            if jobs_remaining:
                print(f"  Quota remaining - Jobs: {jobs_remaining}, Requests: {requests_remaining}")

            # Parse and standardize jobs
            parsed_jobs = [self._parse_job(job) for job in jobs_data]

            return parsed_jobs

        except requests.exceptions.RequestException as e:
            print(f"Error fetching backfill jobs from Active Jobs DB: {e}")
            return []

    def _parse_job(self, job_data: Dict) -> Dict:
        """Parse Active Jobs DB job data into standardized format"""

        # Format salary from raw data
        salary = None
        salary_min = job_data.get('salary_min')
        salary_max = job_data.get('salary_max')
        salary_currency = job_data.get('salary_currency', 'EUR')

        if salary_min and salary_max:
            salary = f"{salary_currency} {salary_min:,} - {salary_max:,}"
        elif salary_min:
            salary = f"{salary_currency} {salary_min:,}+"
        elif salary_max:
            salary = f"Up to {salary_currency} {salary_max:,}"

        # Extract AI-parsed metadata
        ai_data = job_data.get('ai', {}) or {}

        return {
            'job_id': job_data.get('id'),
            'external_id': job_data.get('id'),  # For deduplication
            'title': job_data.get('title'),
            'company': job_data.get('company'),
            'location': job_data.get('location'),
            'description': job_data.get('description', ''),
            'url': job_data.get('url'),
            'posted_date': job_data.get('posted_date'),
            'salary': salary,
            'source': f"Active Jobs DB ({job_data.get('source', 'ATS')})",  # Include ATS platform name
            'fetched_date': job_data.get('fetched_at'),
            'priority': 'medium',  # Default priority for backfill jobs

            # AI-extracted metadata
            'ai_employment_type': ai_data.get('employment_type'),
            'ai_work_arrangement': ai_data.get('work_arrangement'),
            'ai_seniority': ai_data.get('seniority'),
            'ai_industry': ai_data.get('industry'),
            'ai_required_skills': ai_data.get('required_skills', []),
            'ai_optional_skills': ai_data.get('optional_skills', []),
            'ai_responsibilities': ai_data.get('responsibilities', []),

            # Raw data for debugging
            'raw_salary_min': salary_min,
            'raw_salary_max': salary_max,
            'raw_salary_currency': salary_currency,
        }
