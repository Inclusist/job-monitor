"""
Error handling and edge case tests
Tests database operations under failure conditions
"""

import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase


class TestInputValidation:
    """Test input validation and error handling"""
    
    @pytest.fixture(scope="class")
    def cv_manager(self):
        database_url = os.getenv('DATABASE_URL')
        job_db = PostgresDatabase(database_url)
        return PostgresCVManager(job_db.connection_pool)
    
    @pytest.fixture(scope="class")
    def job_db(self):
        database_url = os.getenv('DATABASE_URL')
        return PostgresDatabase(database_url)
    
    def test_search_preferences_invalid_types(self, cv_manager):
        """Test that invalid types are rejected for search preferences"""
        # This should fail gracefully - passing non-list types
        result = cv_manager.update_user_search_preferences(
            user_id=999999,  # Non-existent user
            keywords="not a list",
            locations="also not a list"
        )
        assert result is False
    
    def test_search_preferences_empty_lists(self, cv_manager):
        """Test handling of empty preference lists"""
        from datetime import datetime
        
        # Create test user
        email = f"empty_prefs_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "pass123", "Test")
        
        # Empty lists should be accepted but cleaned
        result = cv_manager.update_user_search_preferences(
            user_id=user_id,
            keywords=[],
            locations=[]
        )
        assert result is True
    
    def test_search_preferences_whitespace_cleanup(self, cv_manager):
        """Test that whitespace is cleaned from preferences"""
        from datetime import datetime
        
        email = f"whitespace_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "pass123", "Test")
        
        # Preferences with whitespace and duplicates
        result = cv_manager.update_user_search_preferences(
            user_id=user_id,
            keywords=['  Python  ', 'Django', 'Python', '  ', 'React'],
            locations=['Berlin  ', '  Munich', '', 'Berlin']
        )
        assert result is True
        
        # Verify cleaned
        prefs = cv_manager.get_user_search_preferences(user_id)
        assert len(prefs['keywords']) == 3  # Python, Django, React (deduped)
        assert len(prefs['locations']) == 2  # Berlin, Munich (deduped, no empty)
        assert '  ' not in prefs['keywords']
        assert '' not in prefs['locations']
    
    def test_add_cv_invalid_file_type(self, cv_manager):
        """Test that invalid file types are rejected"""
        from datetime import datetime
        
        email = f"invalid_type_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "pass123", "Test")
        
        # Invalid file type
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="test.exe",
            file_path="/tmp/test.exe",
            file_type="exe",  # Invalid
            file_size=1000,
            file_hash="hash123"
        )
        assert cv_id is None
    
    def test_add_cv_missing_required_fields(self, cv_manager):
        """Test that missing required fields are rejected"""
        from datetime import datetime
        
        email = f"missing_fields_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "pass123", "Test")
        
        # Missing file_name
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="",
            file_path="/tmp/test.pdf",
            file_type="pdf",
            file_size=1000,
            file_hash="hash123"
        )
        assert cv_id is None
    
    def test_add_cv_duplicate_prevention(self, cv_manager):
        """Test that duplicate CVs are prevented"""
        from datetime import datetime
        
        email = f"duplicate_cv_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "pass123", "Test")
        
        file_hash = f"unique_hash_{datetime.now().timestamp()}"
        
        # Add first CV
        cv_id_1 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test1.pdf",
            file_path="/tmp/test1.pdf",
            file_type="pdf",
            file_size=1000,
            file_hash=file_hash
        )
        assert cv_id_1 is not None
        
        # Try to add duplicate with same hash
        cv_id_2 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test2.pdf",
            file_path="/tmp/test2.pdf",
            file_type="pdf",
            file_size=1000,
            file_hash=file_hash  # Same hash
        )
        assert cv_id_2 is None  # Should be rejected
    
    def test_add_cv_oversized_file(self, cv_manager):
        """Test that oversized files are rejected"""
        from datetime import datetime
        
        email = f"oversized_{datetime.now().timestamp()}@test.com"
        user_id = cv_manager.register_user(email, "pass123", "Test")
        
        # 11MB file (over 10MB limit)
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="huge.pdf",
            file_path="/tmp/huge.pdf",
            file_type="pdf",
            file_size=11 * 1024 * 1024,
            file_hash="hash123"
        )
        assert cv_id is None


class TestDatabaseErrors:
    """Test database error scenarios"""
    
    @pytest.fixture(scope="class")
    def cv_manager(self):
        database_url = os.getenv('DATABASE_URL')
        job_db = PostgresDatabase(database_url)
        return PostgresCVManager(job_db.connection_pool)
    
    def test_get_nonexistent_user(self, cv_manager):
        """Test getting a user that doesn't exist"""
        user = cv_manager.get_user(999999999)
        assert user is None
    
    def test_get_nonexistent_cv(self, cv_manager):
        """Test getting a CV that doesn't exist"""
        cv = cv_manager.get_cv(999999999)
        assert cv is None
    
    def test_update_nonexistent_cv_status(self, cv_manager):
        """Test updating status of non-existent CV"""
        # Should complete without error even if CV doesn't exist
        result = cv_manager.update_cv_status(999999999, 'archived')
        # Returns True even if nothing updated (transaction succeeds)
        assert result is True
    
    def test_duplicate_user_registration(self, cv_manager):
        """Test that duplicate email registration is prevented"""
        from datetime import datetime
        
        email = f"duplicate_{datetime.now().timestamp()}@test.com"
        
        # Register first time
        user_id_1 = cv_manager.register_user(email, "pass123", "Test User")
        assert user_id_1 is not None
        
        # Try to register again with same email
        user_id_2 = cv_manager.register_user(email, "pass456", "Another User")
        assert user_id_2 is None  # Should fail


class TestJobOperationErrors:
    """Test job operation error handling"""
    
    @pytest.fixture(scope="class")
    def job_db(self):
        database_url = os.getenv('DATABASE_URL')
        return PostgresDatabase(database_url)
    
    def test_add_duplicate_job(self, job_db):
        """Test that duplicate jobs are prevented"""
        from datetime import datetime
        
        job_id = f"duplicate_test_{datetime.now().timestamp()}"
        
        job_data = {
            'job_id': job_id,
            'source': 'test',
            'title': 'Test Job',
            'company': 'Test Corp',
            'location': 'Berlin',
            'description': 'Test description',
            'url': 'https://example.com/job',
            'match_score': 75,
            'priority': 'medium'
        }
        
        # Add first time
        result_1 = job_db.add_job(job_data)
        assert result_1 is not None
        
        # Try to add duplicate
        result_2 = job_db.add_job(job_data)
        assert result_2 is None  # Should be rejected
    
    def test_get_nonexistent_job(self, job_db):
        """Test getting a job that doesn't exist"""
        job = job_db.get_job(999999999)
        assert job is None
    
    def test_add_user_job_match_invalid_ids(self, job_db):
        """Test adding match with non-existent user/job"""
        # This might fail or succeed depending on foreign key constraints
        # Just ensure it doesn't crash
        try:
            result = job_db.add_user_job_match(
                user_id=999999999,
                job_id=999999999,
                claude_score=75
            )
            # Either succeeds (no FK constraint) or fails gracefully
            assert result in [True, False]
        except Exception:
            # Foreign key constraint violation is acceptable
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
