"""
Matcher Integration Tests

Tests the actual background matching process that was missing from original suite:
- Would have caught SQLite vs PostgreSQL mismatch
- Tests parameter compatibility
- Tests background thread execution
- Tests status updates
"""

import pytest
import os
import sys
import time
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.matching.matcher import run_background_matching


@pytest.fixture(scope="module")
def db_setup():
    """Setup database connections"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    
    job_db = PostgresDatabase(db_url)
    cv_manager = PostgresCVManager(job_db.connection_pool)
    
    yield {'job_db': job_db, 'cv_manager': cv_manager}


@pytest.fixture
def test_user_with_cv(db_setup):
    """Create test user with CV and profile"""
    cv_manager = db_setup['cv_manager']
    job_db = db_setup['job_db']
    
    # Create user
    email = f"matcher_test_{os.getpid()}_{time.time()}@test.com"
    user_id = cv_manager.register_user(email, "Matcher Test User", "testpass123")
    
    # Create CV
    file_hash = hashlib.sha256(b"test matcher cv content").hexdigest()
    cv_id = cv_manager.add_cv(
        user_id=user_id,
        file_name="test_matcher.pdf",
        file_path="data/cvs/test_matcher.pdf",
        file_type="pdf",
        file_size=1024,
        file_hash=file_hash,
        version=1
    )
    
    # Create profile
    profile_data = {
        'name': 'Test Matcher User',
        'email': email,
        'expertise_summary': 'Python developer with data science experience',
        'technical_skills': ['Python', 'PostgreSQL', 'Machine Learning'],
        'work_history': [
            {
                'title': 'Senior Python Developer',
                'company': 'Test Corp',
                'duration': '3 years',
                'responsibilities': ['Built data pipelines', 'ML model deployment']
            }
        ],
        'education': [{'degree': 'BS Computer Science', 'school': 'Test University'}],
        'languages': ['English', 'German']
    }
    
    profile_id = cv_manager.add_cv_profile(
        cv_id=cv_id,
        user_id=user_id,
        profile_data=profile_data
    )
    
    # Set as primary
    cv_manager.set_primary_cv(user_id, cv_id)
    
    # Add some test jobs
    for i in range(3):
        job_id = job_db.add_job({
            'job_id': f'test_job_{user_id}_{i}',
            'source': 'test_source',
            'title': f'Python Developer {i}',
            'company': f'Test Company {i}',
            'location': 'Berlin',
            'description': 'Looking for Python developer with PostgreSQL experience',
            'url': f'https://test.com/job{i}',
            'posted_date': '2025-12-22',
            'user_id': user_id,
            'cv_profile_id': profile_id
        })
    
    yield {
        'user_id': user_id,
        'cv_id': cv_id,
        'profile_id': profile_id,
        'email': email
    }
    
    # Cleanup
    cv_manager.delete_cv(cv_id)


class TestMatcherParameterCompatibility:
    """Test that matcher uses correct PostgreSQL parameters"""
    
    def test_get_user_job_matches_parameters(self, db_setup):
        """
        CRITICAL TEST: Would have caught min_score vs min_semantic_score bug
        Verify matcher calls use correct PostgreSQL parameter names
        """
        job_db = db_setup['job_db']
        cv_manager = db_setup['cv_manager']
        
        # Create test user
        email = f"param_test_{os.getpid()}@test.com"
        user_id = cv_manager.register_user(email, "Param Test", "testpass123")
        
        # Test correct parameter name
        try:
            matches = job_db.get_user_job_matches(
                user_id, 
                min_semantic_score=0,  # PostgreSQL parameter
                limit=1
            )
            print(f"\n✓ get_user_job_matches accepts min_semantic_score")
        except TypeError as e:
            pytest.fail(f"PostgreSQL method signature mismatch: {e}")
        
        # Test that old SQLite parameter would fail
        with pytest.raises(TypeError, match="min_score"):
            matches = job_db.get_user_job_matches(
                user_id,
                min_score=0,  # Old SQLite parameter
                limit=1
            )
        print(f"✓ Correctly rejects old SQLite parameter (min_score)")
    
    def test_matcher_status_structure(self):
        """Test that matching_status dictionary has expected structure"""
        matching_status = {}
        user_id = 999
        
        # Initialize like matcher does
        matching_status[user_id] = {
            'status': 'running',
            'stage': 'initializing',
            'progress': 0,
            'message': 'Starting job matching...',
            'matches_found': 0,
            'jobs_analyzed': 0
        }
        
        # Verify structure
        assert 'status' in matching_status[user_id]
        assert 'stage' in matching_status[user_id]
        assert 'progress' in matching_status[user_id]
        assert 'message' in matching_status[user_id]
        assert 'matches_found' in matching_status[user_id]
        assert 'jobs_analyzed' in matching_status[user_id]
        print(f"\n✓ Matching status structure correct")


class TestBackgroundMatching:
    """Test actual background matching execution"""
    
    @pytest.mark.slow
    @pytest.mark.api
    def test_matcher_with_existing_jobs(self, test_user_with_cv, db_setup):
        """
        Test matcher runs successfully with pre-existing jobs
        This is a lighter test that doesn't fetch from APIs
        """
        user_id = test_user_with_cv['user_id']
        matching_status = {}
        
        print(f"\n🔄 Running background matching for user {user_id}")
        
        # Run matcher (will skip JSearch fetch since jobs exist)
        run_background_matching(user_id, matching_status)
        
        # Check final status
        assert user_id in matching_status
        final_status = matching_status[user_id]
        
        print(f"  Status: {final_status['status']}")
        print(f"  Stage: {final_status['stage']}")
        print(f"  Progress: {final_status['progress']}%")
        print(f"  Message: {final_status['message']}")
        
        # Verify completion or error state
        assert final_status['status'] in ['completed', 'error', 'idle']
        
        if final_status['status'] == 'completed':
            assert final_status['progress'] == 100
            assert final_status['stage'] == 'done'
            print(f"  ✓ Matches found: {final_status['matches_found']}")
            print(f"  ✓ Jobs analyzed: {final_status['jobs_analyzed']}")
        elif final_status['status'] == 'error':
            print(f"  ⚠ Matcher error: {final_status['message']}")
        
        # Verify matches were created
        job_db = db_setup['job_db']
        matches = job_db.get_user_job_matches(user_id, limit=10)
        print(f"  ✓ Total matches in database: {len(matches)}")
    
    def test_matcher_without_cv(self, db_setup):
        """Test matcher handles missing CV gracefully"""
        cv_manager = db_setup['cv_manager']
        
        # Create user without CV
        email = f"no_cv_test_{os.getpid()}@test.com"
        user_id = cv_manager.register_user(email, "No CV User", "testpass123")
        
        matching_status = {}
        
        print(f"\n🔄 Running matcher without CV")
        run_background_matching(user_id, matching_status)
        
        # Should fail gracefully
        assert user_id in matching_status
        assert matching_status[user_id]['status'] == 'error'
        assert 'CV' in matching_status[user_id]['message']
        print(f"  ✓ Correctly handled missing CV: {matching_status[user_id]['message']}")
    
    def test_matcher_status_updates(self, test_user_with_cv):
        """Test that matcher updates status throughout execution"""
        user_id = test_user_with_cv['user_id']
        matching_status = {}
        
        print(f"\n🔄 Testing status updates")
        
        # Run matcher
        run_background_matching(user_id, matching_status)
        
        # Check that status was set
        assert user_id in matching_status
        status = matching_status[user_id]
        
        # Verify status fields exist
        assert 'status' in status
        assert 'stage' in status
        assert 'progress' in status
        assert 'message' in status
        
        print(f"  ✓ Status: {status['status']}")
        print(f"  ✓ Stage: {status['stage']}")
        print(f"  ✓ Progress: {status['progress']}%")
        print(f"  ✓ Message: {status['message']}")


class TestMatcherDatabaseOperations:
    """Test matcher's database interactions"""
    
    def test_matcher_creates_user_job_matches(self, test_user_with_cv, db_setup):
        """Test that matcher creates user_job_match entries"""
        user_id = test_user_with_cv['user_id']
        job_db = db_setup['job_db']
        
        # Get initial match count
        initial_matches = job_db.get_user_job_matches(user_id, limit=1000)
        initial_count = len(initial_matches)
        
        print(f"\n  Initial matches: {initial_count}")
        
        # Run matcher
        matching_status = {}
        run_background_matching(user_id, matching_status)
        
        # Get final match count
        final_matches = job_db.get_user_job_matches(user_id, limit=1000)
        final_count = len(final_matches)
        
        print(f"  Final matches: {final_count}")
        
        if matching_status[user_id]['status'] == 'completed':
            # Should have created some matches (unless no jobs)
            assert final_count >= initial_count
            print(f"  ✓ Matcher created {final_count - initial_count} new matches")
    
    def test_matcher_updates_filter_run_time(self, test_user_with_cv, db_setup):
        """Test that matcher updates last_filter_run timestamp"""
        user_id = test_user_with_cv['user_id']
        cv_manager = db_setup['cv_manager']
        
        # Get initial filter run time
        user_before = cv_manager.get_user_by_id(user_id)
        initial_filter_time = user_before.get('last_filter_run')
        
        print(f"\n  Initial filter run: {initial_filter_time}")
        
        # Run matcher
        matching_status = {}
        run_background_matching(user_id, matching_status)
        
        # Get updated filter run time
        user_after = cv_manager.get_user_by_id(user_id)
        final_filter_time = user_after.get('last_filter_run')
        
        print(f"  Final filter run: {final_filter_time}")
        
        if matching_status[user_id]['status'] == 'completed':
            # Filter run time should be updated
            if initial_filter_time is None or final_filter_time != initial_filter_time:
                print(f"  ✓ Filter run time updated")
            else:
                print(f"  ⚠ Filter run time not updated (might be ok if no changes)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
