"""
CV Lifecycle Tests

Tests CV state transitions that were missing from original test suite:
- Upload → Delete → Re-upload (CRITICAL: caught production bug)
- Upload → Archive → Re-upload
- Upload → Delete → Upload different CV
- Duplicate prevention across all states
"""

import pytest
import os
import sys
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager


@pytest.fixture(scope="module")
def db_setup():
    """Setup database connections"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    
    job_db = PostgresDatabase(db_url)
    cv_manager = PostgresCVManager(job_db.connection_pool)
    
    yield {'job_db': job_db, 'cv_manager': cv_manager}
    
    # Cleanup handled by individual tests


class TestCVStateTransitions:
    """Test CV state transitions and lifecycle"""
    
    def test_delete_then_reupload_same_cv(self, db_setup):
        """
        CRITICAL TEST: Would have caught production bug
        Test that deleted CVs can be re-uploaded
        """
        cv_manager = db_setup['cv_manager']
        
        # Create test user
        email = f"cv_lifecycle_1_{os.getpid()}@test.com"
        user_id = cv_manager.register_user(email, "Test User", "testpass123")
        assert user_id is not None
        print(f"\n✓ User created: {email} (ID: {user_id})")
        
        # Upload CV
        file_hash = hashlib.sha256(b"test cv content v1").hexdigest()
        cv_id_1 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_cv.pdf",
            file_path="data/cvs/test_cv.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,
            version=1
        )
        assert cv_id_1 is not None
        print(f"✓ CV uploaded (ID: {cv_id_1})")
        
        # Verify CV is active
        cv = cv_manager.get_cv(cv_id_1)
        assert cv['status'] == 'active'
        print(f"✓ CV status: {cv['status']}")
        
        # Delete CV
        cv_manager.delete_cv(cv_id_1)
        cv = cv_manager.get_cv(cv_id_1)
        assert cv['status'] == 'deleted'
        print(f"✓ CV deleted, status: {cv['status']}")
        
        # Re-upload same CV (same hash) - THIS SHOULD WORK
        cv_id_2 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_cv.pdf",
            file_path="data/cvs/test_cv_v2.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,  # Same hash
            version=2
        )
        
        assert cv_id_2 is not None, "Should allow re-upload of deleted CV"
        assert cv_id_2 != cv_id_1, "Should create new CV record"
        print(f"✓ Same CV re-uploaded after deletion (new ID: {cv_id_2})")
        
        # Verify new CV is active
        cv2 = cv_manager.get_cv(cv_id_2)
        assert cv2['status'] == 'active'
        print(f"✓ New CV is active")
        
        # Cleanup
        cv_manager.delete_cv(cv_id_2)
        print("✓ Test cleanup complete")
    
    def test_archive_then_reupload_same_cv(self, db_setup):
        """Test that archived CVs can be re-uploaded"""
        cv_manager = db_setup['cv_manager']
        
        # Create test user
        email = f"cv_lifecycle_2_{os.getpid()}@test.com"
        user_id = cv_manager.register_user(email, "Test User", "testpass123")
        assert user_id is not None
        
        # Upload CV
        file_hash = hashlib.sha256(b"test cv content v2").hexdigest()
        cv_id_1 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_cv.pdf",
            file_path="data/cvs/test_cv.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,
            version=1
        )
        assert cv_id_1 is not None
        
        # Archive CV
        cv_manager.archive_cv(cv_id_1)
        cv = cv_manager.get_cv(cv_id_1)
        assert cv['status'] == 'archived'
        print(f"\n✓ CV archived")
        
        # Re-upload same CV - should work
        cv_id_2 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_cv.pdf",
            file_path="data/cvs/test_cv_v2.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,
            version=2
        )
        
        assert cv_id_2 is not None, "Should allow re-upload of archived CV"
        print(f"✓ Same CV re-uploaded after archiving (new ID: {cv_id_2})")
        
        # Cleanup
        cv_manager.delete_cv(cv_id_2)
    
    def test_prevent_duplicate_active_cv(self, db_setup):
        """Test that duplicate prevention still works for active CVs"""
        cv_manager = db_setup['cv_manager']
        
        # Create test user
        email = f"cv_lifecycle_3_{os.getpid()}@test.com"
        user_id = cv_manager.register_user(email, "Test User", "testpass123")
        
        # Upload CV
        file_hash = hashlib.sha256(b"test cv content v3").hexdigest()
        cv_id_1 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_cv.pdf",
            file_path="data/cvs/test_cv.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,
            version=1
        )
        assert cv_id_1 is not None
        print(f"\n✓ First CV uploaded (ID: {cv_id_1})")
        
        # Try to upload same CV again - should be blocked
        cv_id_2 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_cv_duplicate.pdf",
            file_path="data/cvs/test_cv_dup.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,  # Same hash
            version=1
        )
        
        assert cv_id_2 is None, "Should prevent duplicate active CV"
        print(f"✓ Duplicate active CV correctly blocked")
        
        # Cleanup
        cv_manager.delete_cv(cv_id_1)
    
    def test_delete_then_upload_different_cv(self, db_setup):
        """Test uploading different CV after deleting old one"""
        cv_manager = db_setup['cv_manager']
        
        # Create test user
        email = f"cv_lifecycle_4_{os.getpid()}@test.com"
        user_id = cv_manager.register_user(email, "Test User", "testpass123")
        
        # Upload first CV
        hash1 = hashlib.sha256(b"cv content A").hexdigest()
        cv_id_1 = cv_manager.add_cv(
            user_id=user_id,
            file_name="cv_a.pdf",
            file_path="data/cvs/cv_a.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=hash1,
            version=1
        )
        assert cv_id_1 is not None
        print(f"\n✓ First CV uploaded")
        
        # Delete first CV
        cv_manager.delete_cv(cv_id_1)
        print(f"✓ First CV deleted")
        
        # Upload different CV
        hash2 = hashlib.sha256(b"cv content B").hexdigest()
        cv_id_2 = cv_manager.add_cv(
            user_id=user_id,
            file_name="cv_b.pdf",
            file_path="data/cvs/cv_b.pdf",
            file_type="pdf",
            file_size=2048,
            file_hash=hash2,  # Different hash
            version=1
        )
        
        assert cv_id_2 is not None, "Should allow upload of different CV"
        print(f"✓ Different CV uploaded after deletion (ID: {cv_id_2})")
        
        # Cleanup
        cv_manager.delete_cv(cv_id_2)
    
    def test_multiple_state_transitions(self, db_setup):
        """Test complex state transition sequence"""
        cv_manager = db_setup['cv_manager']
        
        # Create test user
        email = f"cv_lifecycle_5_{os.getpid()}@test.com"
        user_id = cv_manager.register_user(email, "Test User", "testpass123")
        
        file_hash = hashlib.sha256(b"test cv multi-state").hexdigest()
        
        # Upload → Active
        cv_id = cv_manager.add_cv(
            user_id=user_id,
            file_name="test.pdf",
            file_path="data/cvs/test.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,
            version=1
        )
        assert cv_id is not None
        cv = cv_manager.get_cv(cv_id)
        assert cv['status'] == 'active'
        print(f"\n✓ State: active")
        
        # Active → Deleted
        cv_manager.delete_cv(cv_id)
        cv = cv_manager.get_cv(cv_id)
        assert cv['status'] == 'deleted'
        print(f"✓ State: deleted")
        
        # Deleted → Re-upload (new active)
        cv_id_2 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_v2.pdf",
            file_path="data/cvs/test_v2.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,
            version=2
        )
        assert cv_id_2 is not None
        cv2 = cv_manager.get_cv(cv_id_2)
        assert cv2['status'] == 'active'
        print(f"✓ State: active (new record)")
        
        # Active → Archived
        cv_manager.archive_cv(cv_id_2)
        cv2 = cv_manager.get_cv(cv_id_2)
        assert cv2['status'] == 'archived'
        print(f"✓ State: archived")
        
        # Archived → Re-upload (new active)
        cv_id_3 = cv_manager.add_cv(
            user_id=user_id,
            file_name="test_v3.pdf",
            file_path="data/cvs/test_v3.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash=file_hash,
            version=3
        )
        assert cv_id_3 is not None
        cv3 = cv_manager.get_cv(cv_id_3)
        assert cv3['status'] == 'active'
        print(f"✓ State: active (final record)")
        print(f"✓ Complete state transition cycle tested")
        
        # Cleanup
        cv_manager.delete_cv(cv_id_3)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
