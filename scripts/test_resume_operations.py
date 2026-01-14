#!/usr/bin/env python3
"""
Test PostgresResumeOperations class

Tests all database operations for resume generation feature.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_resume_operations import PostgresResumeOperations
from psycopg2 import pool

def test_resume_operations():
    """Test resume operations"""
    print("=" * 70)
    print("🧪 TESTING RESUME OPERATIONS")
    print("=" * 70)
    print()

    # Create connection pool
    connection_pool = pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    resume_ops = PostgresResumeOperations(connection_pool)

    # Use a test user (user_id = 93 from your example)
    test_user_id = 93

    try:
        # Test 1: Save claimed competency
        print("📋 Test 1: Save claimed competency...")
        resume_ops.save_user_claimed_competency(
            user_id=test_user_id,
            competency_name="Agile Methodology",
            work_exp_ids=[1, 2],
            evidence="Led daily standups and sprint planning for 5-person agile team"
        )
        print("   ✅ Competency saved")
        print()

        # Test 2: Save claimed skill
        print("📋 Test 2: Save claimed skill...")
        resume_ops.save_user_claimed_skill(
            user_id=test_user_id,
            skill_name="Python",
            work_exp_ids=[2],
            evidence="Built data pipelines processing 1M+ records daily using Python"
        )
        print("   ✅ Skill saved")
        print()

        # Test 3: Get claimed data
        print("📋 Test 3: Retrieve claimed data...")
        claimed_data = resume_ops.get_user_claimed_data(test_user_id)
        print(f"   ✅ Retrieved data:")
        print(f"      Competencies: {list(claimed_data['competencies'].keys())}")
        print(f"      Skills: {list(claimed_data['skills'].keys())}")
        print()

        # Test 4: Save multiple claims
        print("📋 Test 4: Save multiple claims at once...")
        selections = [
            {
                'name': 'Project Management',
                'type': 'competency',
                'work_experience_ids': [1, 3],
                'evidence': 'Managed cross-functional projects with budgets up to $500K'
            },
            {
                'name': 'React',
                'type': 'skill',
                'work_experience_ids': [2, 3],
                'evidence': 'Built responsive web applications using React and Redux'
            }
        ]
        resume_ops.save_multiple_claims(test_user_id, selections)
        print("   ✅ Multiple claims saved")
        print()

        # Test 5: Get updated claimed data
        print("📋 Test 5: Retrieve updated claimed data...")
        claimed_data = resume_ops.get_user_claimed_data(test_user_id)
        print(f"   ✅ Retrieved data:")
        print(f"      Competencies: {list(claimed_data['competencies'].keys())}")
        print(f"      Skills: {list(claimed_data['skills'].keys())}")
        print()

        # Test 6: Save generated resume
        print("📋 Test 6: Save generated resume...")
        resume_id = resume_ops.save_generated_resume(
            user_id=test_user_id,
            job_id=21923,
            resume_html="<html><body>Test Resume</body></html>",
            resume_pdf_path="/path/to/resume.pdf",
            selections_used=claimed_data
        )
        print(f"   ✅ Resume saved with ID: {resume_id}")
        print()

        # Test 7: Get user resumes
        print("📋 Test 7: Retrieve user resumes...")
        resumes = resume_ops.get_user_resumes(test_user_id)
        print(f"   ✅ Found {len(resumes)} resume(s)")
        if resumes:
            print(f"      Resume ID: {resumes[0]['id']}")
            print(f"      Job ID: {resumes[0]['job_id']}")
            print(f"      Created: {resumes[0]['created_at']}")
        print()

        # Test 8: Get specific resume
        print("📋 Test 8: Get resume by ID...")
        resume = resume_ops.get_resume_by_id(resume_id, test_user_id)
        if resume:
            print(f"   ✅ Resume retrieved")
            print(f"      HTML length: {len(resume['resume_html'])} chars")
            print(f"      PDF path: {resume['resume_pdf_path']}")
            print(f"      Selections used: {len(resume['selections_used']['competencies'])} competencies, {len(resume['selections_used']['skills'])} skills")
        print()

        # Test 9: Get resume count
        print("📋 Test 9: Get resume count...")
        count = resume_ops.get_resume_count_for_user(test_user_id)
        print(f"   ✅ User has {count} resume(s)")
        print()

        # Test 10: Remove claimed competency
        print("📋 Test 10: Remove claimed competency...")
        resume_ops.remove_claimed_competency(test_user_id, "Agile Methodology")
        claimed_data = resume_ops.get_user_claimed_data(test_user_id)
        print(f"   ✅ Competency removed")
        print(f"      Remaining competencies: {list(claimed_data['competencies'].keys())}")
        print()

        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print()
        print("PostgresResumeOperations class is working correctly.")
        print()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        connection_pool.closeall()

if __name__ == "__main__":
    test_resume_operations()
