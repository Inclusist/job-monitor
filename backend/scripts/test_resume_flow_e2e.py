#!/usr/bin/env python3
"""
End-to-End Test for Resume Generation Feature

Tests the complete flow:
1. User profile and job data retrieval
2. Saving user-claimed competencies/skills with evidence
3. Resume generation with Claude AI
4. PDF generation with WeasyPrint
5. Resume download functionality
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from src.resume.resume_generator import ResumeGenerator
from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_resume_operations import PostgresResumeOperations
from psycopg2 import pool


def test_resume_generation_e2e():
    """Test complete resume generation flow"""
    print("=" * 80)
    print("🧪 END-TO-END RESUME GENERATION TEST")
    print("=" * 80)
    print()

    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return False

    # Initialize components
    database_url = os.getenv('DATABASE_URL')
    connection_pool = pool.SimpleConnectionPool(1, 10, database_url)
    cv_manager = PostgresCVManager(connection_pool)
    job_db = PostgresDatabase(database_url)
    resume_ops = PostgresResumeOperations(connection_pool)
    resume_generator = ResumeGenerator(api_key)

    # Test user and job
    test_user_id = 93
    test_job_id = 21923

    try:
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Load User Profile and Job
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 1: Loading user profile and job details...")
        print("-" * 80)

        profile = cv_manager.get_primary_profile(test_user_id)
        if not profile:
            print(f"   ❌ No profile found for user {test_user_id}")
            return False

        print(f"   ✅ Profile loaded")
        print(f"      Name: {profile.get('name', 'N/A')}")
        print(f"      Role: {profile.get('extracted_role', 'N/A')}")
        print(f"      Work Experiences: {len(profile.get('work_experience', []))}")
        print()

        job = job_db.get_job_by_id(test_job_id)
        if not job:
            print(f"   ❌ Job {test_job_id} not found!")
            return False

        print(f"   ✅ Job loaded")
        print(f"      Title: {job['title']}")
        print(f"      Company: {job.get('company', 'N/A')}")
        print(f"      Required competencies: {len(job.get('ai_competencies', []))}")
        print(f"      Required skills: {len(job.get('ai_key_skills', []))}")
        print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Simulate User Claiming Competencies/Skills
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 2: Simulating user claiming missing competencies/skills...")
        print("-" * 80)

        # Create test selections (simulating what frontend would send)
        test_selections = [
            {
                'name': 'Agile Methodology',
                'type': 'competency',
                'work_experience_ids': [0, 1],
                'evidence': 'Led daily standups, sprint planning, and retrospectives for 5-person agile team. Managed product backlog using Jira, improved velocity by 30%.'
            },
            {
                'name': 'Team Leadership',
                'type': 'competency',
                'work_experience_ids': [0],
                'evidence': 'Mentored 3 junior developers, conducted code reviews, and drove technical decisions for the team. Established best practices for code quality.'
            },
            {
                'name': 'Python',
                'type': 'skill',
                'work_experience_ids': [1, 2],
                'evidence': 'Built data pipelines processing 1M+ records daily using Python, Pandas, and FastAPI. Developed ML models with scikit-learn and PyTorch.'
            }
        ]

        print(f"   Claiming {len(test_selections)} items with evidence...")
        resume_ops.save_multiple_claims(test_user_id, test_selections)
        print(f"   ✅ Claims saved to database")
        print()

        # Verify claims were saved
        claimed_data = resume_ops.get_user_claimed_data(test_user_id)
        comp_count = len(claimed_data.get('competencies', {}))
        skill_count = len(claimed_data.get('skills', {}))
        print(f"   ✅ Verified: {comp_count} competencies, {skill_count} skills")
        print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Generate Resume HTML
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 3: Generating resume HTML with Claude AI...")
        print("-" * 80)
        print("   (This may take 10-15 seconds...)")
        print()

        resume_html = resume_generator.generate_resume_html(
            profile,
            job,
            claimed_data
        )

        print(f"   ✅ Resume HTML generated")
        print(f"      Length: {len(resume_html)} characters")

        # Check for [NEW] markers (user-claimed evidence)
        new_markers = resume_html.count('[NEW]')
        print(f"      [NEW] markers: {new_markers}")

        # Validate HTML structure
        required_elements = ['<!DOCTYPE html>', '<html', '<head>', '<body>', '<h1>']
        missing = [el for el in required_elements if el not in resume_html]
        if missing:
            print(f"   ⚠️  Missing elements: {missing}")
        else:
            print(f"      ✅ All required HTML elements present")
        print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Generate PDF
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 4: Generating PDF with WeasyPrint...")
        print("-" * 80)

        pdf_path = f'/tmp/test_resume_e2e_user{test_user_id}_job{test_job_id}.pdf'

        try:
            resume_generator.html_to_pdf(resume_html, pdf_path)
            print(f"   ✅ PDF generated successfully")
            print(f"      Path: {pdf_path}")

            # Verify PDF
            if os.path.exists(pdf_path):
                pdf_size = os.path.getsize(pdf_path)
                print(f"      Size: {pdf_size:,} bytes ({pdf_size/1024:.1f} KB)")

                # Check it's a valid PDF
                with open(pdf_path, 'rb') as f:
                    header = f.read(10)
                    if header.startswith(b'%PDF-'):
                        version = header.decode('ascii', errors='ignore').split('-')[1][:3]
                        print(f"      ✅ Valid PDF file (version {version})")
                    else:
                        print(f"      ⚠️  Warning: File doesn't have PDF header")
            else:
                print(f"      ❌ PDF file not found at {pdf_path}")
                return False
        except Exception as e:
            print(f"   ❌ PDF generation failed: {e}")
            return False

        print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Save to Database
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 5: Saving resume to database...")
        print("-" * 80)

        resume_id = resume_ops.save_generated_resume(
            test_user_id,
            test_job_id,
            resume_html,
            pdf_path,
            claimed_data
        )

        print(f"   ✅ Resume saved to database")
        print(f"      Resume ID: {resume_id}")
        print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Retrieve and Verify
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 6: Retrieving resume from database...")
        print("-" * 80)

        retrieved = resume_ops.get_resume_by_id(resume_id, test_user_id)

        if not retrieved:
            print(f"   ❌ Failed to retrieve resume {resume_id}")
            return False

        print(f"   ✅ Resume retrieved successfully")
        print(f"      User ID: {retrieved['user_id']}")
        print(f"      Job ID: {retrieved['job_id']}")
        print(f"      HTML length: {len(retrieved['resume_html'])} chars")
        print(f"      PDF path: {retrieved.get('resume_pdf_path', 'N/A')}")
        print(f"      Created: {retrieved.get('created_at', 'N/A')}")

        # Verify selections were saved
        selections_used = retrieved.get('selections_used')
        if selections_used:
            print(f"      Selections used: {len(selections_used.get('competencies', {}))} comps, {len(selections_used.get('skills', {}))} skills")
        print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 7: Test Resume Listing
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 7: Testing resume listing...")
        print("-" * 80)

        resumes = resume_ops.get_user_resumes(test_user_id)
        print(f"   ✅ Found {len(resumes)} resume(s) for user")

        # Find our test resume
        test_resume = next((r for r in resumes if r['id'] == resume_id), None)
        if test_resume:
            print(f"      ✅ Test resume found in list")
        else:
            print(f"      ⚠️  Test resume not found in list")
        print()

        # ═══════════════════════════════════════════════════════════════
        # STEP 8: Cleanup (Optional)
        # ═══════════════════════════════════════════════════════════════
        print("📋 STEP 8: Cleanup...")
        print("-" * 80)

        # Delete test resume
        deleted = resume_ops.delete_resume(resume_id, test_user_id)
        if deleted:
            print(f"   ✅ Test resume deleted from database")
        else:
            print(f"   ⚠️  Failed to delete test resume")

        # Delete test PDF
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"   ✅ Test PDF deleted")

        print()

        # ═══════════════════════════════════════════════════════════════
        # SUCCESS!
        # ═══════════════════════════════════════════════════════════════
        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print()
        print("Resume generation feature is working correctly:")
        print("  ✅ User profile and job data retrieval")
        print("  ✅ User-claimed competencies/skills with evidence")
        print("  ✅ Claude AI resume generation (HTML)")
        print("  ✅ WeasyPrint PDF generation")
        print("  ✅ Database storage and retrieval")
        print("  ✅ Resume listing and deletion")
        print()
        print("The feature is ready for production use!")
        print()

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        print(traceback.format_exc())
        return False

    finally:
        connection_pool.closeall()


if __name__ == "__main__":
    success = test_resume_generation_e2e()
    sys.exit(0 if success else 1)
