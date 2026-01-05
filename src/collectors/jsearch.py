"""
JSearch API Collector
Collects jobs from LinkedIn, Indeed, Google Jobs and more via RapidAPI
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime
from .source_filter import SourceFilter


class JSearchCollector:
    """Collects jobs using JSearch API on RapidAPI"""
    
    def __init__(self, api_key: str, enable_filtering: bool = True, min_quality: int = 2):
        """
        Initialize JSearch collector
        
        Args:
            api_key: RapidAPI key for JSearch
            enable_filtering: Whether to filter out low-quality sources
            min_quality: Minimum quality score (1=all, 2=remove spam, 3=only trusted)
        """
        self.api_key = api_key
        self.base_url = "https://jsearch.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        self.enable_filtering = enable_filtering
        self.min_quality = min_quality
        self.source_filter = SourceFilter() if enable_filtering else None
    
    def search_jobs(
        self,
        query: str,
        location: str = None,
        num_pages: int = 1,
        date_posted: str = "week",  # all, today, 3days, week, month
        employment_types: str = None,  # FULLTIME, CONTRACTOR, PARTTIME, INTERN
        remote_jobs_only: bool = False,
        country: str = None  # ISO country code, e.g., "de" for Germany
    ) -> List[Dict]:
        """
        Search for jobs using JSearch API
        
        Args:
            query: Job title or keywords (e.g., "Python Developer")
            location: Location (e.g., "Berlin, Germany")
            num_pages: Number of pages to fetch (10 results per page)
            date_posted: Filter by posting date
            employment_types: Comma-separated list of employment types
            remote_jobs_only: Only return remote jobs
            country: ISO country code (e.g., "de", "us", "gb")
            
        Returns:
            List of job dictionaries
        """
        endpoint = f"{self.base_url}/search"
        
        params = {
            "query": query,
            "num_pages": str(num_pages),
            "date_posted": date_posted,
        }
        
        if location:
            params["query"] = f"{query} in {location}"
        
        if country:
            params["country"] = country
        
        if employment_types:
            params["employment_types"] = employment_types
            
        if remote_jobs_only:
            params["remote_jobs_only"] = "true"
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            # Check for quota/rate limit errors before raising
            if response.status_code == 429:
                error_msg = "Rate limit exceeded"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    pass
                print(f"JSearch API Error 429: {error_msg}")
                print("This could mean: 1) Monthly quota exhausted (200 requests/month), or 2) Rate limit hit (1000/hour)")
                print("Check your RapidAPI dashboard to see remaining quota")
                raise Exception(f"API rate/quota limit: {error_msg}")
            
            response.raise_for_status()
            data = response.json()
            
            print(f"API Response status: {data.get('status')}")
            print(f"Number of results: {len(data.get('data', []))}")
            
            jobs = []
            if data.get("status") == "OK" and data.get("data"):
                for job in data["data"]:
                    parsed_job = self._parse_job(job)

                    # Apply country filter if specified
                    if country and country == 'de':
                        # Only include German jobs
                        job_country = job.get("job_country", "")
                        job_city = job.get("job_city", "")
                        job_state = job.get("job_state", "")

                        # Check if job is in Germany
                        is_german = (
                            job_country == "DE" or
                            "Germany" in str(job_country) or
                            job_city in ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart", "Dusseldorf", "Dortmund", "Essen", "Leipzig", "Bremen", "Dresden", "Hannover", "Nuremberg", "Duisburg", "Bochum", "Wuppertal", "Bielefeld", "Bonn", "Munster", "Karlsruhe", "Mannheim", "Augsburg", "Wiesbaden", "Gelsenkirchen", "Monchengladbach", "Braunschweig", "Chemnitz", "Kiel", "Aachen", "Halle", "Magdeburg", "Freiburg", "Krefeld", "Lubeck", "Oberhausen", "Erfurt", "Mainz", "Rostock", "Kassel", "Hagen", "Hamm", "Saarbrucken", "Mulheim", "Potsdam", "Ludwigshafen", "Oldenburg", "Osnabruck", "Leverkusen", "Solingen", "Heidelberg", "Herne", "Neuss", "Darmstadt", "Paderborn", "Regensburg", "Ingolstadt", "Wurzburg", "Fürth", "Wolfsburg", "Offenbach", "Ulm", "Heilbronn", "Pforzheim", "Gottingen", "Bottrop", "Trier", "Recklinghausen", "Reutlingen", "Bremerhaven", "Koblenz", "Bergisch Gladbach", "Jena", "Remscheid", "Erlangen", "Moers", "Siegen", "Hildesheim", "Salzgitter"]
                        )

                        if not is_german:
                            continue  # Skip non-German jobs

                    jobs.append(parsed_job)
            else:
                print(f"API returned: {data}")

            # Apply source filtering if enabled
            if self.enable_filtering and self.source_filter and jobs:
                print(f"\nApplying source quality filter (min_quality={self.min_quality})...")
                jobs = self.source_filter.filter_jobs(jobs, min_quality=self.min_quality)

            return jobs
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching jobs from JSearch: {e}")
            raise
    
    def _parse_job(self, job_data: Dict) -> Dict:
        """Parse JSearch job data into standardized format"""
        
        # Extract salary info
        salary_min = job_data.get("job_min_salary")
        salary_max = job_data.get("job_max_salary")
        salary_currency = job_data.get("job_salary_currency", "USD")
        
        salary = None
        if salary_min and salary_max:
            salary = f"{salary_currency} {salary_min:,} - {salary_max:,}"
        elif salary_min:
            salary = f"{salary_currency} {salary_min:,}+"
        
        return {
            "title": job_data.get("job_title", ""),
            "company": job_data.get("employer_name", ""),
            "location": job_data.get("job_city") or job_data.get("job_state") or job_data.get("job_country", ""),
            "description": job_data.get("job_description", ""),
            "url": job_data.get("job_apply_link") or job_data.get("job_google_link", ""),
            "salary": salary,
            "employment_type": job_data.get("job_employment_type", ""),
            "posted_date": job_data.get("job_posted_at_datetime_utc", ""),
            "source": "JSearch",
            "external_id": job_data.get("job_id", ""),
            "company_logo": job_data.get("employer_logo"),
            "is_remote": job_data.get("job_is_remote", False),
            "priority": "medium",  # Default priority for all jobs
            "raw_data": job_data
        }
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific job
        
        Args:
            job_id: JSearch job ID
            
        Returns:
            Job details dictionary or None
        """
        endpoint = f"{self.base_url}/job-details"
        
        params = {"job_id": job_id}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK" and data.get("data"):
                return self._parse_job(data["data"][0])
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching job details from JSearch: {e}")
            return None


def test_collector():
    """Test the JSearch collector"""
    api_key = os.getenv("JSEARCH_API_KEY")
    
    if not api_key:
        print("Error: JSEARCH_API_KEY not found in environment")
        return
    
    collector = JSearchCollector(api_key)
    
    print("Testing JSearch API...")
    print("Searching for: Python Developer in Berlin")
    print("-" * 60)
    
    jobs = collector.search_jobs(
        query="Python Developer",
        location="Berlin, Germany",
        num_pages=1,
        date_posted="week",
        country="de"
    )
    
    print(f"\nFound {len(jobs)} jobs\n")
    
    for i, job in enumerate(jobs[:3], 1):
        print(f"{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Salary: {job['salary'] or 'Not specified'}")
        print(f"   Remote: {job['is_remote']}")
        print(f"   Posted: {job['posted_date']}")
        print(f"   URL: {job['url'][:60]}...")
        print()


if __name__ == "__main__":
    test_collector()
