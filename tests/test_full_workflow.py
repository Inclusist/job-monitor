"""
Full workflow integration tests for Job Monitor
Tests the complete flow: user creation -> CV upload -> job search -> job matching

To keep costs low, job searches are limited to 1 keyword + 1 location
"""

import os
import sys
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase
from src.analysis.cv_analyzer import CVAnalyzer
from src.analysis.claude_analyzer import ClaudeJobAnalyzer
from collectors.jsearch import JSearchCollector


@pytest.fixture(scope="module")
def cv_manager():
    """Initialize CV manager"""
    database_url = os.getenv('DATABASE_URL')
    job_db = PostgresDatabase(database_url)
    manager = PostgresCVManager(job_db.connection_pool)
    yield manager
    # Cleanup is handled by test teardown


@pytest.fixture(scope="module")
def job_db():
    """Initialize job database"""
    database_url = os.getenv('DATABASE_URL')
    db = PostgresDatabase(database_url)
    yield db


@pytest.fixture(scope="module")
def test_user(cv_manager):
    """Create a test user and clean up after tests"""
    email = f"test_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.com"
    password = "TestPass123!"
    name = "Workflow Test User"
    
    user_id = cv_manager.register_user(email, password, name)
    assert user_id is not None, "User creation failed"
    
    user = cv_manager.authenticate_user(email, password)
    assert user is not None, "User authentication failed"
    
    yield user
    
    # Cleanup: Archive user's CVs
    try:
        cvs = cv_manager.get_user_cvs(user['id'])
        for cv in cvs:
            cv_manager.archive_cv(cv['id'])
    except Exception as e:
        print(f"Cleanup warning: {e}")


@pytest.fixture(scope="module")
def sample_cv_file():
    """Create a temporary sample CV file"""
    cv_content = """
JOHN DOE
Senior Python Developer & Data Engineer

Email: john.doe@example.com
Phone: +49 123 456 7890
Location: Berlin, Germany

PROFESSIONAL SUMMARY
Experienced Python developer with 8+ years in software development, data engineering, and machine learning.
Specialized in building scalable data pipelines, REST APIs, and cloud-native applications.

SKILLS
- Programming: Python, SQL, JavaScript, TypeScript
- Frameworks: Django, FastAPI, Flask, React
- Data: Pandas, NumPy, Apache Spark, Airflow
- Cloud: AWS (EC2, S3, Lambda), Docker, Kubernetes
- Databases: PostgreSQL, MongoDB, Redis
- ML/AI: Scikit-learn, TensorFlow, PyTorch

WORK EXPERIENCE

Senior Data Engineer | Tech Corp GmbH | Berlin, Germany
Jan 2020 - Present
- Built ETL pipelines processing 10M+ records daily using Apache Airflow and Python
- Designed and implemented RESTful APIs with FastAPI serving 1000+ requests/second
- Reduced data processing time by 60% through optimization and parallel processing
- Led team of 4 engineers in migrating legacy systems to cloud-native architecture

Python Developer | StartUp AG | Munich, Germany
Mar 2017 - Dec 2019
- Developed web applications using Django and React
- Implemented machine learning models for customer segmentation
- Created automated testing suite achieving 90% code coverage
- Collaborated with cross-functional teams in agile environment

EDUCATION
M.Sc. Computer Science | Technical University of Munich | 2017
B.Sc. Computer Science | University of Berlin | 2015

LANGUAGES
- English: Fluent
- German: Professional
"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_file.write(cv_content)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


class TestWorkflowIntegration:
    """Test complete workflow from user creation to job matching"""
    
    def test_01_user_creation(self, test_user):
        """Test user was created successfully"""
        assert test_user is not None
        assert 'id' in test_user
        assert 'email' in test_user
        assert '@test.com' in test_user['email']
        print(f"\n✓ User created: {test_user['email']} (ID: {test_user['id']})")
    
    def test_02_cv_upload(self, cv_manager, test_user, sample_cv_file):
        """Test CV upload and parsing"""
        user_id = test_user['id']
        
        # Upload CV
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_cv.txt",
            file_path=sample_cv_file
        )
        
        assert cv_id is not None, "CV upload failed"
        print(f"✓ CV uploaded: ID {cv_id}")
        
        # Verify CV exists
        cvs = cv_manager.get_user_cvs(user_id)
        assert len(cvs) > 0, "No CVs found for user"
        assert any(cv['id'] == cv_id for cv in cvs), "Uploaded CV not found"
        
        # Parse CV
        cv_analyzer = CVAnalyzer()
        with open(sample_cv_file, 'r') as f:
            cv_text = f.read()
        
        parsed_cv = cv_analyzer.parse_cv(cv_text)
        assert parsed_cv is not None, "CV parsing failed"
        print(f"✓ CV parsed: {len(parsed_cv.get('skills', []))} skills extracted")
        
        # Store CV profile
        profile_id = cv_manager.add_cv_profile(
            cv_id=cv_id,
            parsed_cv=parsed_cv
        )
        
        assert profile_id is not None, "CV profile creation failed"
        print(f"✓ CV profile created: ID {profile_id}")
        
        # Verify profile
        profile = cv_manager.get_cv_profile(cv_id)
        assert profile is not None, "CV profile not found"
        assert len(profile.get('skills', [])) > 0, "No skills in profile"
        assert profile.get('total_years_experience', 0) > 0, "Years of experience not calculated"
        
        print(f"✓ Profile verified: {profile.get('total_years_experience')} years experience")
    
    def test_03_search_preferences(self, cv_manager, test_user):
        """Test setting and retrieving search preferences"""
        user_id = test_user['id']
        
        keywords = ['Python Developer', 'Data Engineer']
        locations = ['Berlin', 'Munich']
        
        success = cv_manager.update_user_search_preferences(
            user_id=user_id,
            keywords=keywords,
            locations=locations
        )
        
        assert success, "Failed to update search preferences"
        print(f"✓ Search preferences updated: {len(keywords)} keywords, {len(locations)} locations")
        
        # Retrieve preferences
        prefs = cv_manager.get_user_search_preferences(user_id)
        assert prefs is not None, "Failed to retrieve preferences"
        assert prefs['keywords'] == keywords, "Keywords mismatch"
        assert prefs['locations'] == locations, "Locations mismatch"
        
        print(f"✓ Preferences verified")
    
    def test_04_limited_job_search(self, job_db, test_user, cv_manager):
        """Test job search with LIMITED API calls (1 search only)"""
        user_id = test_user['id']
        
        # Get CV profile for this user
        cv_profile = cv_manager.get_profile_by_user(user_id)
        assert cv_profile is not None, "CV profile not found"
        
        # Initialize collector with cost-effective settings
        jsearch_key = os.getenv('JSEARCH_API_KEY')
        if not jsearch_key or jsearch_key == 'your_rapidapi_key_for_jsearch':
            pytest.skip("JSearch API key not configured")
        
        collector = JSearchCollector(
            api_key=jsearch_key,
            enable_filtering=True,
            min_quality=2
        )
        
        # Single search to minimize costs
        keyword = 'Python Developer'
        location = 'Berlin'
        
        print(f"\n⚠️  Running LIMITED search: '{keyword}' in '{location}' (cost-effective test)")
        
        jobs = collector.search_jobs(
            query=keyword,
            location=location,
            num_pages=1,  # Only 1 page
            date_posted='week',
            country='de'
        )
        
        assert isinstance(jobs, list), "Search should return a list"
        print(f"✓ Search completed: {len(jobs)} jobs found")
        
        if len(jobs) == 0:
            pytest.skip("No jobs found in search")
        
        # Take only first 5 jobs to minimize Claude API costs
        jobs_to_analyze = jobs[:5]
        
        # Initialize Claude analyzer
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            pytest.skip("Anthropic API key not configured")
        
        analyzer = ClaudeJobAnalyzer(
            api_key=api_key,
            model='claude-3-5-haiku-20241022',  # Use cost-effective model
            db=job_db,
            user_email=test_user['email']
        )
        
        # Set CV profile
        analyzer.set_profile_from_cv(cv_profile.get('parsed_cv', {}))
        
        # Analyze jobs
        analyzed_jobs = []
        for idx, job in enumerate(jobs_to_analyze, 1):
            print(f"  Analyzing job {idx}/{len(jobs_to_analyze)}: {job.get('title', 'Unknown')}")
            analyzed = analyzer.analyze_job(job)
            if analyzed:
                analyzed_jobs.append(analyzed)
        
        print(f"✓ Analysis complete: {len(analyzed_jobs)} jobs scored")
        
        # Store jobs
        stored_count = 0
        job_ids = []
        for job in analyzed_jobs:
            job_id = job_db.add_job(job)
            if job_id:
                stored_count += 1
                job_ids.append(job_id)
        
        assert stored_count > 0, "No jobs were stored"
        print(f"✓ Stored {stored_count} jobs to database")
        
        # Store this for next test
        test_user['_test_job_ids'] = job_ids
        test_user['_cv_profile'] = cv_profile
    
    def test_05_job_matching(self, job_db, cv_manager, test_user):
        """Test matching stored jobs to user"""
        user_id = test_user['id']
        
        # Get job IDs from previous test
        job_ids = test_user.get('_test_job_ids', [])
        cv_profile = test_user.get('_cv_profile')
        
        if not job_ids:
            pytest.skip("No jobs from search test")
        
        print(f"\n✓ Matching {len(job_ids)} jobs to user {user_id}")
        
        # Create user_job_matches for each stored job
        matched_count = 0
        for job_id in job_ids:
            # Get job details
            jobs = job_db.get_jobs_by_date(
                date=datetime.now().strftime('%Y-%m-%d')
            )
            job = next((j for j in jobs if j['id'] == job_id), None)
            
            if job and job.get('match_score'):
                # Determine priority from score
                score = job['match_score']
                if score >= 80:
                    priority = 'high'
                elif score >= 60:
                    priority = 'medium'
                else:
                    priority = 'low'
                
                # Add user job match
                success = job_db.add_user_job_match(
                    user_id=user_id,
                    job_id=job_id,
                    claude_score=score,
                    priority=priority,
                    match_reasoning=job.get('match_reasoning'),
                    key_alignments=job.get('key_alignments', []),
                    potential_gaps=job.get('potential_gaps', [])
                )
                
                if success:
                    matched_count += 1
        
        assert matched_count > 0, "No job matches were created"
        print(f"✓ Created {matched_count} user_job_matches")
        
        # Verify matches exist
        matches = job_db.get_user_job_matches(user_id)
        assert len(matches) > 0, "No matches found for user"
        assert len(matches) == matched_count, "Match count mismatch"
        
        print(f"✓ Verified {len(matches)} matches in database")
        
        # Verify match details
        for match in matches[:3]:  # Check first 3
            assert match.get('claude_score') is not None, "Missing Claude score"
            assert match.get('priority') in ['high', 'medium', 'low'], "Invalid priority"
        
        print(f"✓ Match data integrity verified")
    
    def test_06_match_retrieval(self, job_db, test_user):
        """Test retrieving matched jobs with filters"""
        user_id = test_user['id']
        
        # Get all matches
        all_matches = job_db.get_user_job_matches(user_id)
        assert len(all_matches) > 0, "No matches found"
        print(f"\n✓ Retrieved {len(all_matches)} total matches")
        
        # Filter by Claude score
        high_score_matches = job_db.get_user_job_matches(
            user_id=user_id,
            min_claude_score=70
        )
        print(f"✓ High score matches (≥70): {len(high_score_matches)}")
        
        # Verify each match has required fields
        for match in all_matches:
            assert 'job_id' in match, "Missing job_id"
            assert 'claude_score' in match, "Missing claude_score"
            assert 'priority' in match, "Missing priority"
            
            # Verify job details are joined
            assert 'title' in match or 'job_title' in match, "Missing job title"
        
        print(f"✓ All matches have required fields")
    
    def test_07_statistics(self, cv_manager, job_db, test_user):
        """Test statistics retrieval"""
        user_id = test_user['id']
        
        # CV statistics
        cv_stats = cv_manager.get_cv_statistics(user_id)
        assert cv_stats is not None, "Failed to get CV stats"
        assert cv_stats.get('total_cvs', 0) > 0, "No CVs in stats"
        print(f"\n✓ CV stats: {cv_stats.get('total_cvs')} CVs")
        
        # Job statistics
        job_stats = job_db.get_statistics()
        assert job_stats is not None, "Failed to get job stats"
        print(f"✓ Job stats: {job_stats.get('total_jobs', 0)} total jobs")
        
        # User-specific job count
        matches = job_db.get_user_job_matches(user_id)
        print(f"✓ User has {len(matches)} matched jobs")


class TestDataIntegrity:
    """Test data integrity and edge cases"""
    
    def test_duplicate_job_prevention(self, job_db):
        """Test that duplicate jobs are prevented"""
        job_data = {
            'job_id': f'test_duplicate_{datetime.now().timestamp()}',
            'source': 'test',
            'title': 'Test Job',
            'company': 'Test Company',
            'location': 'Berlin',
            'description': 'Test description',
            'url': 'https://example.com/job',
            'match_score': 75,
            'priority': 'medium'
        }
        
        # Add first time
        job_id_1 = job_db.add_job(job_data)
        assert job_id_1 is not None, "First job add failed"
        
        # Try to add duplicate
        job_id_2 = job_db.add_job(job_data)
        assert job_id_2 is None, "Duplicate job was not prevented"
        
        print("\n✓ Duplicate job prevention working")
    
    def test_cv_status_management(self, cv_manager, test_user):
        """Test CV status updates"""
        user_id = test_user['id']
        
        cvs = cv_manager.get_user_cvs(user_id)
        if not cvs:
            pytest.skip("No CVs to test")
        
        cv_id = cvs[0]['id']
        
        # Update status
        success = cv_manager.update_cv_status(cv_id, 'archived')
        assert success, "Failed to update CV status"
        
        # Verify status change
        updated_cv = cv_manager.get_cv(cv_id)
        assert updated_cv['status'] == 'archived', "Status not updated"
        
        # Restore status
        cv_manager.update_cv_status(cv_id, 'active')
        
        print("\n✓ CV status management working")


def run_tests():
    """Run tests with verbose output"""
    import subprocess
    
    result = subprocess.run(
        ['pytest', __file__, '-v', '--tb=short', '-s'],
        cwd=Path(__file__).parent.parent
    )
    
    return result.returncode


if __name__ == '__main__':
    print("="*70)
    print("Job Monitor - Full Workflow Integration Tests")
    print("="*70)
    print("\nThese tests cover:")
    print("  1. User creation and authentication")
    print("  2. CV upload and parsing")
    print("  3. Search preferences management")
    print("  4. LIMITED job search (5 jobs max to minimize costs)")
    print("  5. Job matching to user")
    print("  6. Match retrieval and filtering")
    print("  7. Statistics")
    print("  8. Data integrity checks")
    print("\n⚠️  Note: Tests will make actual API calls but are limited to reduce costs")
    print("="*70)
    print()
    
    exit_code = run_tests()
    sys.exit(exit_code)
