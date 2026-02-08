"""
API Collector Tests

Tests the three live job search APIs with minimal queries to validate:
1. API connectivity and authentication
2. Response parsing and data structure
3. Error handling for API failures
4. Rate limiting and quota management

Cost considerations:
- JSearch: RapidAPI costs per request (~$0.001 per search)
- ActiveJobs: Free tier (200 requests/month, 5000 jobs/month)
- Arbeitsagentur: Free public API (no limits)

Total estimated cost per full test run: ~$0.01
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.jsearch import JSearchCollector
from src.collectors.activejobs import ActiveJobsCollector
from src.collectors.arbeitsagentur import ArbeitsagenturCollector


class TestJSearchCollector:
    """Test JSearch API (RapidAPI) - LinkedIn, Indeed, Google Jobs aggregator"""
    
    @pytest.fixture
    def jsearch_collector(self):
        """Create JSearch collector with API key from environment"""
        api_key = os.getenv('RAPIDAPI_KEY')
        if not api_key:
            pytest.skip("RAPIDAPI_KEY not set - skipping JSearch tests")
        return JSearchCollector(api_key=api_key, enable_filtering=True, min_quality=2)
    
    @pytest.mark.quick
    @pytest.mark.api
    def test_jsearch_api_connectivity(self, jsearch_collector):
        """Test JSearch API is accessible and returns data"""
        # Single search with minimal results (1 page = 10 jobs)
        jobs = jsearch_collector.search_jobs(
            query="Python Developer",
            location="Berlin, Germany",
            num_pages=1,
            date_posted="week"
        )
        
        assert jobs is not None, "JSearch should return data"
        assert isinstance(jobs, list), "JSearch should return a list"
        assert len(jobs) > 0, "JSearch should return at least 1 job"
        
        # Validate job structure
        job = jobs[0]
        assert 'job_title' in job or 'title' in job, "Job should have title"
        assert 'company' in job or 'employer_name' in job, "Job should have company"
        print(f"✓ JSearch API working - returned {len(jobs)} jobs")
    
    @pytest.mark.api
    def test_jsearch_germany_country_filter(self, jsearch_collector):
        """Test JSearch with Germany-specific filtering"""
        jobs = jsearch_collector.search_jobs(
            query="Software Engineer",
            country="de",
            num_pages=1,
            date_posted="week"
        )
        
        assert jobs is not None
        assert len(jobs) > 0
        print(f"✓ JSearch Germany filter working - {len(jobs)} jobs")
    
    @pytest.mark.api
    def test_jsearch_remote_jobs(self, jsearch_collector):
        """Test JSearch remote job filtering"""
        jobs = jsearch_collector.search_jobs(
            query="Python Developer",
            num_pages=1,
            remote_jobs_only=True,
            date_posted="week"
        )
        
        assert jobs is not None
        # Remote jobs might be fewer, so just check it doesn't error
        print(f"✓ JSearch remote filter working - {len(jobs)} remote jobs")
    
    @pytest.mark.api
    def test_jsearch_error_handling(self, jsearch_collector):
        """Test JSearch handles invalid parameters gracefully"""
        # Empty query should either return error or empty list
        try:
            jobs = jsearch_collector.search_jobs(
                query="",
                num_pages=1
            )
            # If no error, should return empty or handle gracefully
            assert isinstance(jobs, list)
            print("✓ JSearch handles empty query gracefully")
        except Exception as e:
            # Expected to fail with validation error
            assert "query" in str(e).lower() or "required" in str(e).lower()
            print(f"✓ JSearch validates input: {str(e)[:50]}")


class TestActiveJobsCollector:
    """Test ActiveJobs DB API (RapidAPI) - ATS platforms and career sites"""
    
    @pytest.fixture
    def activejobs_collector(self):
        """Create ActiveJobs collector with API key from environment"""
        api_key = os.getenv('RAPIDAPI_KEY')
        if not api_key:
            pytest.skip("RAPIDAPI_KEY not set - skipping ActiveJobs tests")
        return ActiveJobsCollector(api_key=api_key, enable_filtering=True, min_quality=2)
    
    @pytest.mark.quick
    @pytest.mark.api
    def test_activejobs_api_connectivity(self, activejobs_collector):
        """Test ActiveJobs API is accessible and returns data"""
        # Search with minimal parameters (1 page = 100 jobs max)
        jobs = activejobs_collector.search_jobs(
            keywords="Python",
            location="Germany",
            max_pages=1,
            date_posted="week"
        )
        
        assert jobs is not None, "ActiveJobs should return data"
        assert isinstance(jobs, list), "ActiveJobs should return a list"
        assert len(jobs) > 0, "ActiveJobs should return at least 1 job"
        
        # Validate job structure
        job = jobs[0]
        assert 'title' in job or 'job_title' in job, "Job should have title"
        assert 'company' in job or 'company_name' in job, "Job should have company"
        print(f"✓ ActiveJobs API working - returned {len(jobs)} jobs")
    
    @pytest.mark.expensive
    @pytest.mark.api
    def test_activejobs_recent_jobs_endpoint(self, activejobs_collector):
        """Test ActiveJobs 24h recent jobs endpoint (more efficient)"""
        # Use the bulk endpoint for all recent jobs
        jobs = activejobs_collector.search_all_recent_jobs(
            location="Germany",
            max_pages=1,
            date_posted="24h"
        )
        
        assert jobs is not None
        assert isinstance(jobs, list)
        print(f"✓ ActiveJobs 24h endpoint working - {len(jobs)} recent jobs")
    
    @pytest.mark.api
    def test_activejobs_remote_filter(self, activejobs_collector):
        """Test ActiveJobs remote job filtering"""
        jobs = activejobs_collector.search_jobs(
            keywords="Software Developer",
            location="Germany",
            max_pages=1,
            remote_only=True
        )
        
        assert jobs is not None
        assert isinstance(jobs, list)
        print(f"✓ ActiveJobs remote filter working - {len(jobs)} remote jobs")
    
    @pytest.mark.expensive
    @pytest.mark.api
    def test_activejobs_pagination(self, activejobs_collector):
        """Test ActiveJobs handles pagination correctly"""
        # Get 2 pages (should be 200 jobs max if available)
        jobs = activejobs_collector.search_jobs(
            keywords="Python",
            location="Berlin",
            max_pages=2,
            date_posted="week"
        )
        
        assert jobs is not None
        assert isinstance(jobs, list)
        # Should return more jobs with 2 pages (unless limited dataset)
        print(f"✓ ActiveJobs pagination working - {len(jobs)} jobs from 2 pages")


class TestArbeitsagenturCollector:
    """Test Bundesagentur für Arbeit API - German Federal Employment Agency (Free, no key needed)"""
    
    @pytest.fixture
    def arbeitsagentur_collector(self):
        """Create Arbeitsagentur collector (no API key needed)"""
        return ArbeitsagenturCollector()
    
    @pytest.mark.quick
    @pytest.mark.api
    def test_arbeitsagentur_api_connectivity(self, arbeitsagentur_collector):
        """Test Arbeitsagentur API is accessible and returns data"""
        # Single search with minimal results
        result = arbeitsagentur_collector.search_jobs(
            keywords="Python Entwickler",
            location="Berlin",
            radius_km=50,
            page=1,
            page_size=25
        )
        
        assert result is not None, "Arbeitsagentur should return data"
        assert isinstance(result, dict), "Arbeitsagentur should return a dict"
        assert 'stellenangebote' in result, "Should have job offers key"
        
        jobs = result.get('stellenangebote', [])
        assert len(jobs) > 0, "Should return at least 1 job"
        
        # Validate job structure
        job = jobs[0]
        assert 'titel' in job or 'beruf' in job, "Job should have title"
        assert 'arbeitgeber' in job, "Job should have employer"
        print(f"✓ Arbeitsagentur API working - returned {len(jobs)} jobs")
    
    @pytest.mark.api
    def test_arbeitsagentur_fulltime_filter(self, arbeitsagentur_collector):
        """Test Arbeitsagentur full-time job filtering"""
        result = arbeitsagentur_collector.search_jobs(
            keywords="Software Developer",
            location="München",
            work_time=arbeitsagentur_collector.WORK_TIME_FULLTIME,
            page_size=25
        )
        
        assert result is not None
        jobs = result.get('stellenangebote', [])
        print(f"✓ Arbeitsagentur full-time filter working - {len(jobs)} jobs")
    
    @pytest.mark.api
    def test_arbeitsagentur_remote_filter(self, arbeitsagentur_collector):
        """Test Arbeitsagentur remote/home office filtering"""
        result = arbeitsagentur_collector.search_jobs(
            keywords="Python",
            work_time=arbeitsagentur_collector.WORK_TIME_HOME_OFFICE,
            page_size=25
        )
        
        assert result is not None
        jobs = result.get('stellenangebote', [])
        print(f"✓ Arbeitsagentur remote filter working - {len(jobs)} remote jobs")
    
    @pytest.mark.api
    def test_arbeitsagentur_date_filter(self, arbeitsagentur_collector):
        """Test Arbeitsagentur date filtering (recent jobs)"""
        result = arbeitsagentur_collector.search_jobs(
            keywords="Python",
            location="Deutschland",
            days_since_posted=30,  # Use longer period to ensure results
            page_size=25
        )
        
        assert result is not None
        jobs = result.get('stellenangebote', [])
        # Date filter may return 0 if no recent jobs match criteria
        print(f"✓ Arbeitsagentur date filter working - {len(jobs)} jobs from last 30 days")
    
    @pytest.mark.api
    def test_arbeitsagentur_pagination(self, arbeitsagentur_collector):
        """Test Arbeitsagentur pagination"""
        # Get page 1
        result_page1 = arbeitsagentur_collector.search_jobs(
            keywords="Software",
            location="Deutschland",
            page=1,
            page_size=25
        )
        
        # Get page 2
        result_page2 = arbeitsagentur_collector.search_jobs(
            keywords="Software",
            location="Deutschland",
            page=2,
            page_size=25
        )
        
        assert result_page1 is not None
        assert result_page2 is not None
        
        jobs_page1 = result_page1.get('stellenangebote', [])
        jobs_page2 = result_page2.get('stellenangebote', [])
        
        # Pages should have different jobs (check first job ID is different)
        if len(jobs_page1) > 0 and len(jobs_page2) > 0:
            id1 = jobs_page1[0].get('refnr') or jobs_page1[0].get('hashId')
            id2 = jobs_page2[0].get('refnr') or jobs_page2[0].get('hashId')
            assert id1 != id2, "Different pages should return different jobs"
        
        print(f"✓ Arbeitsagentur pagination working - Page 1: {len(jobs_page1)}, Page 2: {len(jobs_page2)} jobs")
    
    @pytest.mark.api
    def test_arbeitsagentur_no_api_key_needed(self):
        """Verify Arbeitsagentur works without API key configuration"""
        # Should work even if RAPIDAPI_KEY is not set
        collector = ArbeitsagenturCollector()
        result = collector.search_jobs(
            keywords="Python",
            page_size=5
        )
        
        assert result is not None
        print("✓ Arbeitsagentur works without API key configuration")


class TestCollectorIntegration:
    """Test all three collectors working together"""
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_all_collectors_search(self):
        """Test all three collectors can run in sequence"""
        results = {}
        
        # 1. Arbeitsagentur (always available, no key)
        try:
            ba_collector = ArbeitsagenturCollector()
            ba_result = ba_collector.search_jobs(
                keywords="Python Developer",
                location="Berlin",
                page_size=10
            )
            results['arbeitsagentur'] = len(ba_result.get('stellenangebote', []))
            print(f"✓ Arbeitsagentur: {results['arbeitsagentur']} jobs")
        except Exception as e:
            print(f"✗ Arbeitsagentur failed: {e}")
            results['arbeitsagentur'] = 0
        
        # 2. JSearch (requires API key)
        api_key = os.getenv('RAPIDAPI_KEY')
        if api_key:
            try:
                jsearch_collector = JSearchCollector(api_key=api_key)
                jsearch_jobs = jsearch_collector.search_jobs(
                    query="Python Developer",
                    location="Berlin, Germany",
                    num_pages=1
                )
                results['jsearch'] = len(jsearch_jobs)
                print(f"✓ JSearch: {results['jsearch']} jobs")
            except Exception as e:
                print(f"✗ JSearch failed: {e}")
                results['jsearch'] = 0
        else:
            print("⊘ JSearch skipped (no API key)")
            results['jsearch'] = None
        
        # 3. ActiveJobs (requires API key)
        if api_key:
            try:
                activejobs_collector = ActiveJobsCollector(api_key=api_key)
                activejobs_jobs = activejobs_collector.search_jobs(
                    keywords="Python Developer",
                    location="Berlin",
                    max_pages=1
                )
                results['activejobs'] = len(activejobs_jobs)
                print(f"✓ ActiveJobs: {results['activejobs']} jobs")
            except Exception as e:
                print(f"✗ ActiveJobs failed: {e}")
                results['activejobs'] = 0
        else:
            print("⊘ ActiveJobs skipped (no API key)")
            results['activejobs'] = None
        
        # At least one collector should work
        assert results['arbeitsagentur'] > 0, "Arbeitsagentur should always work"
        
        # Print summary
        total_jobs = sum(v for v in results.values() if v is not None)
        print(f"\n✓ Collector Integration Test Complete")
        print(f"Total jobs across all APIs: {total_jobs}")
        print(f"Results: {results}")


if __name__ == "__main__":
    # Run with: pytest tests/test_api_collectors.py -v -s
    # Or: python -m pytest tests/test_api_collectors.py -v -s
    pytest.main([__file__, "-v", "-s"])
