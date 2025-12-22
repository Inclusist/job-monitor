"""
Integration tests for complete workflows
Tests the full flow without external API calls (mocked)
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase


class TestSearchToMatchFlow:
    """Test complete search-to-match workflow"""
    
    @pytest.fixture(scope="class")
    def setup(self):
        """Setup test database instances"""
        database_url = os.getenv('DATABASE_URL')
        job_db = PostgresDatabase(database_url)
        cv_manager = PostgresCVManager(job_db.connection_pool)
        
        return {
            'job_db': job_db,
            'cv_manager': cv_manager
        }
    
    def test_complete_user_journey(self, setup):
        """Test complete user journey from registration to job matches"""
        from datetime import datetime
        
        cv_manager = setup['cv_manager']
        job_db = setup['job_db']
        
        # Step 1: User registration
        email = f"journey_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "SecurePass123!", "Journey User")
        assert user_id is not None
        print(f"\n✓ User registered: {email} (ID: {user_id})")
        
        # Step 2: User login
        user = cv_manager.authenticate_user(email, "SecurePass123!")
        assert user is not None
        assert user['id'] == user_id
        print(f"✓ User authenticated")
        
        # Step 3: Upload CV
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="resume.pdf",
            file_path=f"/tmp/resume_{user_id}.pdf",
            file_type="pdf",
            file_size=50000,
            file_hash=f"hash_{datetime.now().timestamp()}"
        )
        assert cv_id is not None
        print(f"✓ CV uploaded (ID: {cv_id})")
        
        # Step 4: Add CV profile
        profile_data = {
            'expertise_summary': 'Senior Python Developer with 8 years experience',
            'technical_skills': ['Python', 'Django', 'PostgreSQL', 'AWS'],
            'total_years_experience': 8,
            'work_history': [
                {
                    'company': 'Tech Corp',
                    'position': 'Senior Developer',
                    'duration': '2018-2025',
                    'description': 'Led development team'
                }
            ],
            'education': [
                {
                    'degree': 'M.Sc. Computer Science',
                    'institution': 'University',
                    'year': '2016'
                }
            ]
        }
        
        profile_id = cv_manager.add_cv_profile(cv_id, user_id, profile_data)
        assert profile_id is not None
        print(f"✓ CV profile created (ID: {profile_id})")
        
        # Step 5: Set search preferences
        success = cv_manager.update_user_search_preferences(
            user_id=user_id,
            keywords=['Python Developer', 'Backend Engineer'],
            locations=['Berlin', 'Remote']
        )
        assert success is True
        print(f"✓ Search preferences set")
        
        # Step 6: Simulate job search results (would come from API)
        mock_jobs = [
            {
                'job_id': f'integration_test_job_1_{datetime.now().timestamp()}',
                'source': 'test',
                'title': 'Senior Python Developer',
                'company': 'Example GmbH',
                'location': 'Berlin',
                'description': 'Looking for senior Python developer with Django experience',
                'url': 'https://example.com/job1',
                'match_score': 88,
                'match_reasoning': 'Strong match - Python, Django, senior level',
                'key_alignments': ['Python', 'Django', 'Senior level'],
                'potential_gaps': ['AWS certification'],
                'priority': 'high'
            },
            {
                'job_id': f'integration_test_job_2_{datetime.now().timestamp()}',
                'source': 'test',
                'title': 'Backend Developer',
                'company': 'Startup AG',
                'location': 'Remote',
                'description': 'Backend developer needed',
                'url': 'https://example.com/job2',
                'match_score': 72,
                'match_reasoning': 'Good match - Backend, Remote',
                'key_alignments': ['Python', 'Backend'],
                'potential_gaps': ['Microservices experience'],
                'priority': 'medium'
            }
        ]
        
        # Step 7: Store jobs and create matches (simulating fixed app.py)
        stored_jobs = []
        for job in mock_jobs:
            job_id = job_db.add_job(job)
            if job_id:
                stored_jobs.append(job_id)
                # Create user_job_match
                match_success = job_db.add_user_job_match(
                    user_id=user_id,
                    job_id=job_id,
                    claude_score=job.get('match_score'),
                    priority=job.get('priority'),
                    match_reasoning=job.get('match_reasoning'),
                    key_alignments=job.get('key_alignments', []),
                    potential_gaps=job.get('potential_gaps', [])
                )
                assert match_success is True
        
        assert len(stored_jobs) == 2
        print(f"✓ Stored {len(stored_jobs)} jobs with user matches")
        
        # Step 8: Retrieve user's job matches
        matches = job_db.get_user_job_matches(user_id)
        assert len(matches) >= 2
        print(f"✓ Retrieved {len(matches)} job matches")
        
        # Step 9: Filter by score
        high_score_matches = job_db.get_user_job_matches(
            user_id=user_id,
            min_claude_score=80
        )
        assert len(high_score_matches) >= 1
        print(f"✓ High score matches (≥80): {len(high_score_matches)}")
        
        # Step 10: Verify match data integrity
        for match in matches:
            assert 'claude_score' in match
            assert 'priority' in match
            assert match['priority'] in ['high', 'medium', 'low']
            # Job details should be joined
            assert 'title' in match or 'job_title' in match
        
        print(f"✓ All match data validated")
        print(f"\n✅ Complete user journey successful!")


class TestConcurrentOperations:
    """Test concurrent database operations"""
    
    @pytest.fixture(scope="class")
    def setup(self):
        database_url = os.getenv('DATABASE_URL')
        job_db = PostgresDatabase(database_url)
        cv_manager = PostgresCVManager(job_db.connection_pool)
        
        return {
            'job_db': job_db,
            'cv_manager': cv_manager
        }
    
    def test_multiple_users_same_cv_hash(self, setup):
        """Test that different users can have CVs with same content (hash)"""
        from datetime import datetime
        
        cv_manager = setup['cv_manager']
        
        # Same file hash (e.g., both uploaded the same template)
        file_hash = f"shared_template_{datetime.now().timestamp()}"
        
        # User 1
        email1 = f"user1_{datetime.now().timestamp()}@test.com"
        user_id_1 = cv_manager.register_user(email1, "pass123", "User 1")
        cv_id_1 = cv_manager.add_cv(
            user_id=user_id_1,
            file_name="resume1.pdf",
            file_path="/tmp/resume1.pdf",
            file_type="pdf",
            file_size=1000,
            file_hash=file_hash
        )
        assert cv_id_1 is not None
        
        # User 2 with same hash
        email2 = f"user2_{datetime.now().timestamp()}@test.com"
        user_id_2 = cv_manager.register_user(email2, "pass123", "User 2")
        cv_id_2 = cv_manager.add_cv(
            user_id=user_id_2,
            file_name="resume2.pdf",
            file_path="/tmp/resume2.pdf",
            file_type="pdf",
            file_size=1000,
            file_hash=file_hash
        )
        # Different users CAN have same hash
        assert cv_id_2 is not None
        assert cv_id_1 != cv_id_2
        
        print(f"\n✓ Different users can upload same CV content")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])
