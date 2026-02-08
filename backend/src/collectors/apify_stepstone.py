"""
Apify StepStone Collector
Collects jobs from StepStone using Apify's actor
"""

import requests
import os
import time
from typing import List, Dict, Optional


class ApifyStepStoneCollector:
    """Collects jobs from StepStone using Apify"""
    
    def __init__(self, api_token: str):
        """
        Initialize Apify StepStone collector
        
        Args:
            api_token: Apify API token
        """
        self.api_token = api_token
        self.base_url = "https://api.apify.com/v2"
        # Using a popular StepStone scraper actor
        # You may need to find the correct actor ID for StepStone
        self.actor_id = "nGccjr2T5R5wkIgKF"  # Example - replace with actual StepStone actor
    
    def search_jobs(
        self,
        query: str,
        location: str = None,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Search for jobs on StepStone
        
        Args:
            query: Job search query
            location: Location (e.g., "Berlin")
            max_results: Maximum number of results to return
            
        Returns:
            List of job dictionaries
        """
        # Build search URL for StepStone
        base_stepstone_url = "https://www.stepstone.de/stellenangebote--"
        search_url = f"{base_stepstone_url}{query.replace(' ', '-')}"
        
        if location:
            search_url += f"-in-{location.replace(' ', '-')}"
        
        # Prepare actor input
        actor_input = {
            "startUrls": [{"url": search_url}],
            "maxResults": max_results,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        try:
            # Start the actor
            run_url = f"{self.base_url}/acts/{self.actor_id}/runs?token={self.api_token}"
            response = requests.post(run_url, json=actor_input)
            response.raise_for_status()
            run_data = response.json()
            
            run_id = run_data["data"]["id"]
            print(f"Started Apify actor run: {run_id}")
            
            # Wait for the run to complete
            jobs = self._wait_for_results(run_id)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            print(f"Error running Apify actor: {e}")
            return []
    
    def _wait_for_results(self, run_id: str, max_wait: int = 300) -> List[Dict]:
        """
        Wait for actor run to complete and fetch results
        
        Args:
            run_id: Actor run ID
            max_wait: Maximum time to wait in seconds
            
        Returns:
            List of parsed jobs
        """
        status_url = f"{self.base_url}/actor-runs/{run_id}?token={self.api_token}"
        dataset_url = f"{self.base_url}/actor-runs/{run_id}/dataset/items?token={self.api_token}"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check run status
                response = requests.get(status_url)
                response.raise_for_status()
                status_data = response.json()
                
                status = status_data["data"]["status"]
                
                if status == "SUCCEEDED":
                    # Fetch results
                    response = requests.get(dataset_url)
                    response.raise_for_status()
                    results = response.json()
                    
                    jobs = []
                    for item in results:
                        parsed = self._parse_job(item)
                        if parsed:
                            jobs.append(parsed)
                    
                    return jobs
                    
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    print(f"Actor run {status}: {run_id}")
                    return []
                
                # Still running, wait
                time.sleep(5)
                print(f"Waiting for results... ({status})")
                
            except requests.exceptions.RequestException as e:
                print(f"Error checking run status: {e}")
                return []
        
        print(f"Timeout waiting for results after {max_wait}s")
        return []
    
    def _parse_job(self, job_data: Dict) -> Optional[Dict]:
        """Parse Apify StepStone job data into standardized format"""
        
        # The exact structure depends on the actor used
        # This is a generic parser - adjust based on actual output
        
        try:
            return {
                "title": job_data.get("title") or job_data.get("jobTitle", ""),
                "company": job_data.get("company") or job_data.get("companyName", ""),
                "location": job_data.get("location", ""),
                "description": job_data.get("description") or job_data.get("jobDescription", ""),
                "url": job_data.get("url") or job_data.get("jobUrl", ""),
                "salary": job_data.get("salary"),
                "employment_type": job_data.get("employmentType") or job_data.get("jobType", ""),
                "posted_date": job_data.get("postedDate") or job_data.get("publishedAt", ""),
                "source": "StepStone (Apify)",
                "external_id": job_data.get("id") or job_data.get("jobId", ""),
                "raw_data": job_data
            }
        except Exception as e:
            print(f"Error parsing job: {e}")
            return None


def test_collector():
    """Test the Apify StepStone collector"""
    api_token = os.getenv("APIFY_API_TOKEN")
    
    if not api_token:
        print("Error: APIFY_API_TOKEN not found in environment")
        return
    
    collector = ApifyStepStoneCollector(api_token)
    
    print("Testing Apify StepStone scraper...")
    print("Searching for: Python Developer in Berlin")
    print("-" * 60)
    print("Note: This may take 30-60 seconds...\n")
    
    jobs = collector.search_jobs(
        query="Python Developer",
        location="Berlin",
        max_results=10
    )
    
    print(f"\nFound {len(jobs)} jobs\n")
    
    for i, job in enumerate(jobs[:3], 1):
        print(f"{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   URL: {job['url'][:60]}...")
        print()


if __name__ == "__main__":
    test_collector()
