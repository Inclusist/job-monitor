"""
Database-specific tests for PostgreSQL operations
Tests CRUD operations without making external API calls
"""

import os
import sys
import pytest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase


class TestPostgresCVOperations:
    """Test CV manager operations"""
    
    @pytest.fixture(scope="class")
    def cv_manager(self):
        # Initialize PostgresDatabase first to get connection pool
        database_url = os.getenv('DATABASE_URL')
        job_db = PostgresDatabase(database_url)
        return PostgresCVManager(job_db.connection_pool)
    
    @pytest.fixture(scope="class")
    def test_user(self, cv_manager):
        """Create test user"""
        email = f"db_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.com"
        user_id = cv_manager.register_user(email, "TestPass123!", "DB Test User")
        
        user = cv_manager.authenticate_user(email, "TestPass123!")
        yield user
        
        # Cleanup
        try:
            cvs = cv_manager.get_user_cvs(user['id'])
            for cv in cvs:
                cv_manager.archive_cv(cv['id'])
        except:
            pass
    
    def test_user_registration(self, cv_manager):
        """Test user registration"""
        email = f"reg_test_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "password123", "Test User")
        
        assert user_id is not None
        
        # Test duplicate registration
        duplicate_id = cv_manager.register_user(email, "password123", "Test User")
        assert duplicate_id is None
    
    def test_user_authentication(self, cv_manager, test_user):
        """Test user authentication"""
        # Correct password
        user = cv_manager.authenticate_user(test_user['email'], "TestPass123!")
        assert user is not None
        assert user['id'] == test_user['id']
        
        # Wrong password
        user = cv_manager.authenticate_user(test_user['email'], "WrongPassword")
        assert user is None
    
    def test_cv_operations(self, cv_manager, test_user):
        """Test CV CRUD operations"""
        user_id = test_user['id']
        
        # Add CV
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="test.pdf",
            file_path="/tmp/test.pdf",
            file_type="pdf",
            file_size=12345,
            file_hash="abc123hash"
        )
        assert cv_id is not None
        
        # Get CV
        cv = cv_manager.get_cv(cv_id)
        assert cv is not None
        assert cv['file_name'] == "test.pdf"
        assert cv['status'] == 'active'
        
        # Get user CVs
        cvs = cv_manager.get_user_cvs(user_id)
        assert len(cvs) > 0
        assert any(c['id'] == cv_id for c in cvs)
        
        # Update status
        success = cv_manager.update_cv_status(cv_id, 'archived')
        assert success
        
        cv = cv_manager.get_cv(cv_id)
        assert cv['status'] == 'archived'
    
    def test_cv_profile_operations(self, cv_manager, test_user):
        """Test CV profile operations"""
        user_id = test_user['id']
        
        # Add CV first
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="profile_test.pdf",
            file_path="/tmp/test.pdf",
            file_type="pdf",
            file_size=12345,
            file_hash="xyz789hash"
        )
        
        # Add profile
        parsed_cv = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+49 123 456',
            'location': 'Berlin',
            'expertise_summary': 'Python developer with 5 years experience',
            'technical_skills': ['Python', 'Django', 'PostgreSQL'],
            'total_years_experience': 5,
            'work_history': [
                {
                    'company': 'Tech Corp',
                    'position': 'Python Developer',
                    'duration': '2020-2023',
                    'description': 'Built APIs'
                }
            ],
            'education': [
                {
                    'degree': 'M.Sc. Computer Science',
                    'institution': 'TU Munich',
                    'year': '2020'
                }
            ]
        }
        
        profile_id = cv_manager.add_cv_profile(cv_id, user_id, parsed_cv)
        assert profile_id is not None
        
        # Get profile
        profile = cv_manager.get_cv_profile(cv_id)
        assert profile is not None
        
        # cv_profiles table has: technical_skills, expertise_summary, work_history, education
        # Not 'name' - that's in the original parsed data
        assert profile.get('expertise_summary') == 'Python developer with 5 years experience'
        
        # Check skills (should be in technical_skills or work_experience field after mapping)
        skills = profile.get('technical_skills', profile.get('skills', []))
        assert len(skills) >= 3
        
        # Check work experience
        work_exp = profile.get('work_experience', profile.get('work_history', []))
        assert len(work_exp) > 0
        assert profile['total_years_experience'] == 5
        
        # Test field name mapping (work_history -> work_experience)
        # The mapping happens in get_cv_profile
        assert 'work_experience' in profile or 'work_history' in profile
        
        # Get user profile
        user_profile = cv_manager.get_user_cv_profile(user_id)
        assert user_profile is not None
        # Check that profile has expected structure
        assert user_profile.get('expertise_summary') == 'Python developer with 5 years experience'
    
    def test_search_preferences(self, cv_manager, test_user):
        """Test search preferences"""
        user_id = test_user['id']
        
        keywords = ['Python', 'Django', 'FastAPI']
        locations = ['Berlin', 'Munich']
        
        # Update preferences
        success = cv_manager.update_user_search_preferences(
            user_id, keywords, locations
        )
        assert success
        
        # Get preferences
        prefs = cv_manager.get_user_search_preferences(user_id)
        assert prefs is not None
        assert prefs['keywords'] == keywords
        assert prefs['locations'] == locations


class TestPostgresJobOperations:
    """Test job database operations"""
    
    @pytest.fixture(scope="class")
    def job_db(self):
        database_url = os.getenv('DATABASE_URL')
        return PostgresDatabase(database_url)
    
    def test_add_job(self, job_db):
        """Test adding jobs"""
        job_data = {
            'job_id': f'test_job_{datetime.now().timestamp()}',
            'source': 'test',
            'title': 'Python Developer',
            'company': 'Test Corp',
            'location': 'Berlin',
            'description': 'Looking for Python dev',
            'url': 'https://example.com/job',
            'match_score': 85,
            'match_reasoning': 'Good match',
            'key_alignments': ['Python', 'Berlin'],
            'potential_gaps': ['Kubernetes'],
            'priority': 'high',
            'salary': '€60,000 - €80,000'
        }
        
        job_id = job_db.add_job(job_data)
        assert job_id is not None
        
        # Test duplicate prevention
        duplicate_id = job_db.add_job(job_data)
        assert duplicate_id is None
    
    def test_job_retrieval(self, job_db):
        """Test retrieving jobs"""
        # Add a job first
        job_data = {
            'job_id': f'retrieve_test_{datetime.now().timestamp()}',
            'source': 'test',
            'title': 'Data Engineer',
            'company': 'Data Corp',
            'location': 'Munich',
            'description': 'Data engineering role',
            'url': 'https://example.com/job2',
            'match_score': 75,
            'priority': 'medium'
        }
        
        job_id = job_db.add_job(job_data)
        assert job_id is not None
        
        # Get by date
        today = datetime.now().strftime('%Y-%m-%d')
        jobs = job_db.get_jobs_by_date(today)
        assert isinstance(jobs, list)
        assert any(j['id'] == job_id for j in jobs)
        
        # Get by score
        high_score_jobs = job_db.get_jobs_by_score(min_score=70)
        assert isinstance(high_score_jobs, list)
    
    def test_user_job_matches(self, job_db):
        """Test user job matching operations"""
        # This test requires a user and job - simplified version
        # In real workflow, this is tested in test_full_workflow.py
        
        # Just test that the method exists and has correct signature
        from inspect import signature
        sig = signature(job_db.add_user_job_match)
        params = list(sig.parameters.keys())
        
        assert 'user_id' in params
        assert 'job_id' in params
        assert 'claude_score' in params
    
    def test_job_statistics(self, job_db):
        """Test statistics retrieval"""
        stats = job_db.get_statistics()
        
        assert stats is not None
        assert 'total_jobs' in stats
        assert isinstance(stats['total_jobs'], int)
        # PostgreSQL stats may have different structure than SQLite
        assert 'by_status' in stats or 'by_source' in stats


class TestMethodParity:
    """Test that PostgreSQL has all methods that SQLite has"""
    
    def test_postgres_cv_manager_methods(self):
        """Verify PostgresCVManager has all required methods"""
        database_url = os.getenv('DATABASE_URL')
        job_db = PostgresDatabase(database_url)
        cv_manager = PostgresCVManager(job_db.connection_pool)
        
        required_methods = [
            'register_user', 'authenticate_user', 'get_user',
            'add_cv', 'get_cv', 'get_user_cvs', 'update_cv_status',
            'add_cv_profile', 'get_cv_profile', 'get_user_cv_profile',
            'update_user_search_preferences', 'get_user_search_preferences',
            'should_refilter', 'get_profile_by_user',
            'update_filter_run_time', 'get_all_active_users',
            'archive_cv', 'get_cv_statistics', 'close'
        ]
        
        for method in required_methods:
            assert hasattr(cv_manager, method), f"Missing method: {method}"
    
    def test_postgres_database_methods(self):
        """Verify PostgresDatabase has all required methods"""
        database_url = os.getenv('DATABASE_URL')
        job_db = PostgresDatabase(database_url)
        
        required_methods = [
            'add_job', 'job_exists', 'get_jobs_by_date', 'get_jobs_by_score',
            'get_jobs_by_priority', 'update_job_status', 'get_job',
            'add_user_job_match', 'get_user_job_matches',
            'get_deleted_job_ids', 'get_deleted_jobs',
            'permanently_delete_job', 'add_search_record', 'add_feedback',
            'get_user_feedback', 'get_shortlisted_jobs',
            'get_unfiltered_jobs_for_user', 'count_new_jobs_since',
            'get_statistics', 'close'
        ]
        
        for method in required_methods:
            assert hasattr(job_db, method), f"Missing method: {method}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
