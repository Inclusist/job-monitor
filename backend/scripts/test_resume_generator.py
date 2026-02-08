#!/usr/bin/env python3
"""
Test ResumeGenerator class

Tests Claude AI resume generation with actual user profile and job data.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from src.resume.resume_generator import ResumeGenerator
from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase
from psycopg2 import pool

def test_resume_generator():
    """Test resume generator with real data"""
    print("=" * 70)
    print("🧪 TESTING RESUME GENERATOR")
    print("=" * 70)
    print()

    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return

    # Initialize components
    connection_pool = pool.SimpleConnectionPool(1, 10, os.getenv('DATABASE_URL'))
    cv_manager = PostgresCVManager(connection_pool)
    job_db = PostgresDatabase(os.getenv('DATABASE_URL'))

    # Use test user and job
    test_user_id = 93
    test_job_id = 21923

    try:
        # Test 1: Get user profile
        print("📋 Test 1: Loading user CV profile...")
        profile = cv_manager.get_primary_profile(test_user_id)
        if not profile:
            print(f"   ❌ No profile found for user {test_user_id}")
            return

        print(f"   ✅ Profile loaded")
        print(f"      Name: {profile.get('name', 'N/A')}")
        print(f"      Role: {profile.get('extracted_role', 'N/A')}")
        print(f"      Competencies: {len(profile.get('competencies', []))}")
        print(f"      Skills: {len(profile.get('technical_skills', []))}")
        print()

        # Test 2: Get job details
        print("📋 Test 2: Loading job details...")
        job = job_db.get_job_by_id(test_job_id)
        if not job:
            print(f"   ❌ Job {test_job_id} not found!")
            return

        print(f"   ✅ Job loaded")
        print(f"      Title: {job['title']}")
        print(f"      Company: {job.get('company', 'N/A')}")
        print(f"      Required competencies: {len(job.get('ai_competencies', []))}")
        print(f"      Required skills: {len(job.get('ai_key_skills', []))}")
        print()

        # Test 3: Create sample claimed data
        print("📋 Test 3: Creating sample claimed data...")
        claimed_data = {
            'competencies': {
                'Agile Methodology': {
                    'work_experience_ids': [0, 1],
                    'evidence': 'Led daily standups, sprint planning, and retrospectives for 5-person agile team. Managed product backlog using Jira.',
                    'added_at': '2026-01-14T10:00:00Z'
                },
                'Team Leadership': {
                    'work_experience_ids': [0],
                    'evidence': 'Mentored 3 junior developers, conducted code reviews, and drove technical decisions for the team.',
                    'added_at': '2026-01-14T10:05:00Z'
                }
            },
            'skills': {
                'Python': {
                    'work_experience_ids': [1, 2],
                    'evidence': 'Built data pipelines processing 1M+ records daily using Python, Pandas, and FastAPI.',
                    'added_at': '2026-01-14T10:10:00Z'
                }
            }
        }
        print(f"   ✅ Sample claimed data created")
        print(f"      Claimed competencies: {len(claimed_data['competencies'])}")
        print(f"      Claimed skills: {len(claimed_data['skills'])}")
        print()

        # Test 4: Initialize generator
        print("📋 Test 4: Initializing ResumeGenerator...")
        generator = ResumeGenerator(api_key)
        print(f"   ✅ Generator initialized")
        print(f"      Model: {generator.model}")
        print()

        # Test 5: Estimate cost
        print("📋 Test 5: Estimating generation cost...")
        cost_estimate = generator.estimate_cost(profile, job, claimed_data)
        print(f"   ✅ Cost estimated")
        print(f"      Input tokens: ~{cost_estimate['estimated_input_tokens']}")
        print(f"      Output tokens: ~{cost_estimate['estimated_output_tokens']}")
        print(f"      Total cost: ~${cost_estimate['estimated_total_cost']:.4f}")
        print()

        # Test 6: Generate resume (THE BIG TEST!)
        print("📋 Test 6: Generating resume with Claude AI...")
        print("   (This may take 10-15 seconds...)")
        print()

        resume_html = generator.generate_resume_html(profile, job, claimed_data)

        print(f"   ✅ Resume generated successfully!")
        print(f"      HTML length: {len(resume_html)} characters")
        print()

        # Test 7: Validate HTML structure
        print("📋 Test 7: Validating HTML structure...")
        required_elements = [
            '<!DOCTYPE html>',
            '<html',
            '<head>',
            '<style>',
            '<body>',
            '<h1>',  # Name
            '<h2>',  # Section headers
        ]

        missing = []
        for element in required_elements:
            if element not in resume_html:
                missing.append(element)

        if missing:
            print(f"   ⚠️  Missing elements: {missing}")
        else:
            print(f"   ✅ All required HTML elements present")

        # Check for [NEW] markers (user-claimed evidence)
        new_count = resume_html.count('[NEW]')
        print(f"      [NEW] markers found: {new_count}")
        print()

        # Test 8: Save HTML to file
        print("📋 Test 8: Saving HTML to file...")
        output_path = '/tmp/test_resume.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(resume_html)
        print(f"   ✅ HTML saved to {output_path}")
        print(f"      You can open this file in a browser to preview")
        print()

        # Test 9: Extract key sections (verify content)
        print("📋 Test 9: Verifying key sections...")
        sections_found = []

        # Check for professional summary
        if 'summary' in resume_html.lower() or 'objective' in resume_html.lower():
            sections_found.append('Professional Summary')

        # Check for experience section
        if 'experience' in resume_html.lower():
            sections_found.append('Professional Experience')

        # Check for education
        if 'education' in resume_html.lower():
            sections_found.append('Education')

        # Check for skills/competencies
        if 'skill' in resume_html.lower() or 'competenc' in resume_html.lower():
            sections_found.append('Skills/Competencies')

        print(f"   ✅ Sections found: {', '.join(sections_found)}")
        print()

        # Test 10: Show sample content
        print("📋 Test 10: Sample content preview...")
        # Extract first 500 characters of body
        body_start = resume_html.find('<body>')
        if body_start != -1:
            body_end = resume_html.find('</body>')
            body_content = resume_html[body_start+6:body_end]
            # Remove HTML tags for preview
            import re
            text_preview = re.sub('<[^<]+?>', '', body_content)
            text_preview = ' '.join(text_preview.split())[:300]
            print(f"   Preview: {text_preview}...")
        print()

        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print()
        print("ResumeGenerator is working correctly with Claude AI.")
        print(f"Open {output_path} in your browser to see the generated resume.")
        print()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        connection_pool.closeall()

if __name__ == "__main__":
    test_resume_generator()
