"""
End-to-end test for complete job matching pipeline
Tests the entire flow from CV upload to semantic matching to Claude analysis
"""
import pytest
import os
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.matching.matcher import run_background_matching
from src.analysis.claude_analyzer import ClaudeJobAnalyzer


# Sample CV text for testing
SAMPLE_CV_TEXT = """
John Smith
Senior Software Engineer
john.smith@example.com | +1-555-0123 | LinkedIn: linkedin.com/in/johnsmith

PROFESSIONAL SUMMARY
Experienced software engineer with 8+ years in full-stack development, specializing in 
Python, React, and cloud infrastructure. Strong background in building scalable web 
applications and microservices. Expert in PostgreSQL, Docker, and AWS.

TECHNICAL SKILLS
- Languages: Python, JavaScript, TypeScript, SQL
- Frameworks: Django, Flask, React, Node.js
- Databases: PostgreSQL, MongoDB, Redis
- Cloud & DevOps: AWS (EC2, RDS, S3), Docker, Kubernetes, CI/CD
- Tools: Git, Jenkins, Terraform

WORK EXPERIENCE

Senior Software Engineer | Tech Corp Inc. | 2020 - Present
- Lead development of microservices architecture serving 1M+ users
- Implemented CI/CD pipelines reducing deployment time by 60%
- Mentored 5 junior engineers in best practices and code reviews
- Technologies: Python, Django, PostgreSQL, Docker, AWS

Software Engineer | StartupXYZ | 2017 - 2020
- Built REST APIs and web applications using Python and React
- Optimized database queries improving performance by 40%
- Developed automated testing framework with 85% code coverage
- Technologies: Python, Flask, React, PostgreSQL

EDUCATION
Bachelor of Science in Computer Science
University of Technology | 2013 - 2017

CERTIFICATIONS
- AWS Certified Solutions Architect
- Python Professional Certificate
"""

# Sample job posting
SAMPLE_JOB = {
    'job_id': 'test-job-12345',
    'source': 'test',
    'title': 'Senior Backend Engineer',
    'company': 'Amazing Tech Company',
    'location': 'Berlin, Germany',
    'description': """
We are looking for a Senior Backend Engineer to join our growing team!

Requirements:
- 5+ years of experience with Python development
- Strong knowledge of PostgreSQL and database optimization
- Experience with Django or Flask frameworks
- Familiarity with Docker and container orchestration
- Cloud platform experience (AWS preferred)
- Strong problem-solving and communication skills

Responsibilities:
- Design and implement scalable backend services
- Optimize database performance and queries
- Collaborate with frontend team on API design
- Mentor junior developers
- Participate in code reviews and architecture discussions

Nice to have:
- Experience with microservices architecture
- Knowledge of CI/CD pipelines
- React or other frontend framework experience

We offer competitive salary, remote work options, and great benefits!
    """,
    'url': 'https://example.com/jobs/test-12345',
    'posted_date': datetime.now(),
    'salary': '€70,000 - €90,000',
    'status': 'active'
}


@pytest.fixture
def db():
    """Get database instance"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    return PostgresDatabase(db_url)


@pytest.fixture
def cv_manager(db):
    """Get CV manager instance"""
    return PostgresCVManager(db.connection_pool)


@pytest.fixture
def test_user(cv_manager):
    """Create a test user for e2e testing"""
    email = f"e2e_test_{datetime.now().timestamp()}@test.com"
    user_id = cv_manager.register_user(email, "test_password123", "E2E Test User")
    
    yield {'id': user_id, 'email': email}
    
    # Cleanup: delete user and related data
    try:
        cv_manager.delete_user(user_id)
    except:
        pass


@pytest.fixture
def test_cv(cv_manager, test_user):
    """Create and upload a test CV"""
    # Create a temporary CV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(SAMPLE_CV_TEXT)
        cv_path = f.name
    
    try:
        # Upload CV
        import hashlib
        file_hash = hashlib.md5(SAMPLE_CV_TEXT.encode()).hexdigest()
        
        cv_id = cv_manager.save_cv(
            user_id=test_user['id'],
            file_name='test_cv.txt',
            file_path=cv_path,
            file_type='text/plain',
            file_size=len(SAMPLE_CV_TEXT),
            file_hash=file_hash
        )
        
        # Parse and create profile
        profile_data = {
            'expertise_summary': 'Senior Software Engineer with 8+ years in full-stack development',
            'technical_skills': ['Python', 'JavaScript', 'TypeScript', 'SQL', 'Django', 'Flask', 'React', 
                      'PostgreSQL', 'Docker', 'AWS', 'Kubernetes'],
            'soft_skills': ['Leadership', 'Mentoring', 'Problem Solving'],
            'languages': ['English'],
            'education': ['Bachelor of Science in Computer Science'],
            'work_history': [
                'Senior Software Engineer at Tech Corp Inc. (2020-Present)',
                'Software Engineer at StartupXYZ (2017-2020)'
            ],
            'achievements': [
                'Implemented CI/CD pipelines reducing deployment time by 60%',
                'Led development of microservices architecture serving 1M+ users'
            ],
            'career_level': 'Senior',
            'preferred_roles': ['Backend Engineer', 'Full Stack Engineer', 'Technical Lead'],
            'industries': ['Technology', 'Software Development'],
            'raw_analysis': {'full_text': SAMPLE_CV_TEXT}
        }
        
        cv_manager.save_cv_profile(cv_id, test_user['id'], profile_data)
        cv_manager.set_primary_cv(test_user['id'], cv_id)
        
        yield {'id': cv_id, 'profile': profile_data}
        
    finally:
        # Cleanup temp file
        if os.path.exists(cv_path):
            os.unlink(cv_path)


@pytest.fixture
def test_job(db):
    """Create a test job posting"""
    job_id = db.add_job(SAMPLE_JOB)
    
    yield {'id': job_id, **SAMPLE_JOB}
    
    # Cleanup: delete job
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        conn.commit()
        cursor.close()
        db._return_connection(conn)
    except:
        pass


class TestMatchingEndToEnd:
    """End-to-end tests for complete matching pipeline"""
    
    def test_fetch_user_info(self, cv_manager, test_user, test_cv):
        """Test fetching user information"""
        # Fetch user
        user = cv_manager.get_user_by_id(test_user['id'])
        assert user is not None
        assert user['email'] == test_user['email']
        
        # Fetch primary CV
        primary_cv = cv_manager.get_primary_cv(test_user['id'])
        assert primary_cv is not None
        assert primary_cv['id'] == test_cv['id']
        assert primary_cv['is_primary'] == 1  # PostgreSQL returns 1 for true
        
        # Fetch CV profile
        profile = cv_manager.get_cv_profile(test_cv['id'], include_full_text=False)
        assert profile is not None
        assert profile.get('expertise_summary') is not None
        assert profile['technical_skills'] is not None
        assert len(profile['technical_skills']) > 0
    
    def test_fetch_job_posting(self, db, test_job):
        """Test fetching job posting"""
        # Fetch by database ID
        job = db.get_job(test_job['id'])
        assert job is not None
        assert job['title'] == 'Senior Backend Engineer'
        assert job['company'] == 'Amazing Tech Company'
        assert 'Python' in job['description']
        assert 'PostgreSQL' in job['description']
        
        # Verify job details
        assert job['location'] == 'Berlin, Germany'
        assert job['status'] == 'new'  # Default status
    
    def test_semantic_matching(self, db, cv_manager, test_user, test_cv, test_job):
        """Test semantic matching between CV and job"""
        # Import semantic matching components
        from pathlib import Path
        import importlib.util
        
        scripts_dir = Path(__file__).parent.parent / 'scripts'
        filter_jobs_path = scripts_dir / 'filter_jobs.py'
        
        if not filter_jobs_path.exists():
            pytest.skip("filter_jobs.py not found")
        
        # Load filter_jobs module
        spec = importlib.util.spec_from_file_location("filter_module", filter_jobs_path)
        filter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(filter_module)
        
        # Load semantic model
        model = filter_module.load_sentence_transformer()
        assert model is not None
        
        # Build CV text and embedding
        profile = cv_manager.get_cv_profile(test_cv['id'], include_full_text=False)
        cv_text = filter_module.build_cv_text(profile)
        cv_embedding = model.encode(cv_text, show_progress_bar=False)
        assert cv_embedding is not None
        assert len(cv_embedding) > 0
        
        # Get job and calculate similarity  
        job = db.get_job(test_job['id'])
        
        # Build job text and embedding
        job_text = filter_module.build_job_text(job)
        job_embedding = model.encode(job_text, show_progress_bar=False)
        
        # Calculate similarity
        similarity = filter_module.calculate_similarity(cv_embedding, job_embedding)
        assert similarity > 0, "Similarity should be > 0"
        
        # Apply keyword boosts
        config_keywords = {
            'skills': ['python', 'postgresql', 'docker', 'aws', 'django', 'flask'],
            'titles': ['senior', 'engineer', 'developer', 'backend']
        }
        boosted_score, matched_keywords = filter_module.apply_keyword_boosts(
            similarity, job, config_keywords
        )
        
        # Assertions
        assert boosted_score >= 0.3, f"Boosted score should be >= 0.3, got {boosted_score}"
        assert len(matched_keywords) > 0, f"Should have matched keywords, got: {matched_keywords}"
        
        print(f"\n✓ Semantic match successful!")
        print(f"  Similarity: {similarity:.3f}")
        print(f"  Boosted score: {int(boosted_score * 100)}%")
        print(f"  Matched keywords: {', '.join(matched_keywords[:10])}")
    
    def test_batch_insert_matches(self, db, test_user, test_job):
        """Test batch insert of job matches"""
        # Prepare batch matches
        batch_matches = [
            {
                'user_id': test_user['id'],
                'job_id': test_job['id'],
                'semantic_score': 75,
                'match_reasoning': 'Python, PostgreSQL, Docker skills match'
            }
        ]
        
        # Batch insert
        saved_count = db.add_user_job_matches_batch(batch_matches)
        assert saved_count == 1, "Should save 1 match"
        
        # Verify match was saved
        matches = db.get_user_job_matches(test_user['id'], min_semantic_score=0)
        assert len(matches) >= 1, "Should have at least 1 match"
        
        # Note: get_user_job_matches returns 'job_id' as the string identifier (e.g., 'test-job-12345')
        # not the database table id. We need to compare using the job's string identifier.
        user_match = next((m for m in matches if m['job_id'] == test_job['job_id']), None)
        assert user_match is not None, f"Should find our test job match with job_id={test_job['job_id']}"
        assert user_match['semantic_score'] == 75
        assert 'Python' in user_match['match_reasoning']
        
        print(f"\n✓ Batch insert successful!")
        print(f"  Matches saved: {saved_count}")
        print(f"  Match reasoning: {user_match['match_reasoning']}")
    
    def test_large_batch_insert(self, db, test_user):
        """Test batch insert with many matches (simulates real usage)"""
        # Create 100 test matches
        batch_matches = []
        for i in range(100):
            batch_matches.append({
                'user_id': test_user['id'],
                'job_id': 1000 + i,  # Fake job IDs for testing
                'semantic_score': 30 + (i % 70),  # Scores between 30-99
                'match_reasoning': f'Test match {i}'
            })
        
        # Time the batch insert
        import time
        start_time = time.time()
        saved_count = db.add_user_job_matches_batch(batch_matches)
        elapsed = time.time() - start_time
        
        assert saved_count == 100, "Should save all 100 matches"
        assert elapsed < 2.0, f"Batch insert should complete in <2s, took {elapsed:.2f}s"
        
        print(f"\n✓ Large batch insert successful!")
        print(f"  Matches saved: {saved_count}")
        print(f"  Time elapsed: {elapsed:.3f}s")
        print(f"  Performance: {saved_count / elapsed:.1f} matches/second")
    
    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    def test_claude_analysis(self, db, cv_manager, test_user, test_cv, test_job):
        """Test Claude analysis on matched job"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Initialize Claude analyzer
        analyzer = ClaudeJobAnalyzer(
            api_key=api_key,
            db=db,
            user_email=test_user['email']
        )
        
        # Set profile
        profile = cv_manager.get_cv_profile(test_cv['id'], include_full_text=False)
        analyzer.set_profile(profile)
        
        # Get job
        job = db.get_job(test_job['id'])
        
        # Run Claude analysis
        analysis = analyzer.analyze_job(job)
        
        # Assertions
        assert analysis is not None, "Analysis should not be None"
        assert 'match_score' in analysis, "Should have match_score"
        assert 'key_alignments' in analysis, "Should have key_alignments"
        assert 'potential_gaps' in analysis, "Should have potential_gaps"
        assert 'priority' in analysis, "Should have priority"
        
        # Match score should be high (CV and job are well-aligned)
        assert analysis['match_score'] >= 60, f"Match score should be >= 60, got {analysis['match_score']}"
        
        # Should have some alignments
        assert len(analysis['key_alignments']) > 0, "Should have key alignments"
        
        # Verify alignments mention relevant skills
        alignments_text = ' '.join(analysis['key_alignments']).lower()
        assert 'python' in alignments_text or 'backend' in alignments_text or 'engineer' in alignments_text
        
        print(f"\n✓ Claude analysis successful!")
        print(f"  Match score: {analysis['match_score']}%")
        print(f"  Priority: {analysis['priority']}")
        print(f"  Key alignments: {len(analysis['key_alignments'])}")
        print(f"  Potential gaps: {len(analysis['potential_gaps'])}")
        
        # Print first alignment as example
        if analysis['key_alignments']:
            print(f"  Example alignment: {analysis['key_alignments'][0]}")
    
    def test_complete_matching_pipeline(self, db, cv_manager, test_user, test_cv, test_job):
        """Test complete end-to-end matching pipeline"""
        # Step 1: Verify user and CV setup
        user = cv_manager.get_user_by_id(test_user['id'])
        assert user is not None
        
        primary_cv = cv_manager.get_primary_cv(test_user['id'])
        assert primary_cv is not None
        
        profile = cv_manager.get_cv_profile(test_cv['id'], include_full_text=False)
        assert profile is not None
        
        print("\n" + "="*60)
        print("COMPLETE MATCHING PIPELINE TEST")
        print("="*60)
        print(f"\n1. User Setup:")
        print(f"   ✓ User ID: {test_user['id']}")
        print(f"   ✓ Email: {test_user['email']}")
        print(f"   ✓ CV uploaded: {primary_cv['file_name']}")
        print(f"   ✓ Profile expertise: {profile.get('expertise_summary', 'N/A')[:50]}...")
        
        # Step 2: Verify job exists
        job = db.get_job(test_job['id'])
        assert job is not None
        
        print(f"\n2. Job Posting:")
        print(f"   ✓ Job ID: {test_job['id']}")
        print(f"   ✓ Title: {job['title']}")
        print(f"   ✓ Company: {job['company']}")
        print(f"   ✓ Location: {job['location']}")
        
        # Step 3: Run semantic matching
        from pathlib import Path
        import importlib.util
        
        scripts_dir = Path(__file__).parent.parent / 'scripts'
        filter_jobs_path = scripts_dir / 'filter_jobs.py'
        
        if not filter_jobs_path.exists():
            pytest.skip("filter_jobs.py not found")
        
        spec = importlib.util.spec_from_file_location("filter_module", filter_jobs_path)
        filter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(filter_module)
        
        model = filter_module.load_sentence_transformer()
        cv_text = filter_module.build_cv_text(profile)
        cv_embedding = model.encode(cv_text, show_progress_bar=False)
        
        # Build job text and embedding
        job_text = filter_module.build_job_text(job)
        job_embedding = model.encode(job_text, show_progress_bar=False)
        
        # Calculate similarity
        similarity = filter_module.calculate_similarity(cv_embedding, job_embedding)
        
        # Apply keyword boosts
        config_keywords = {
            'skills': ['python', 'postgresql', 'docker', 'aws', 'django', 'flask'],
            'titles': ['senior', 'engineer', 'developer', 'backend']
        }
        boosted_score, matched_keywords = filter_module.apply_keyword_boosts(
            similarity, job, config_keywords
        )
        
        assert boosted_score >= 0.3
        match = {
            'job': job,
            'score': int(boosted_score * 100),
            'matched_keywords': matched_keywords
        }
        
        print(f"\n3. Semantic Matching:")
        print(f"   ✓ Match found: {match['job']['title']}")
        print(f"   ✓ Score: {match['score']}%")
        print(f"   ✓ Keywords: {', '.join(match['matched_keywords'][:5])}")
        
        # Step 4: Save match to database
        batch_matches = [{
            'user_id': test_user['id'],
            'job_id': test_job['id'],
            'semantic_score': match['score'],
            'match_reasoning': f"Matched keywords: {', '.join(match['matched_keywords'][:5])}"
        }]
        
        saved_count = db.add_user_job_matches_batch(batch_matches)
        assert saved_count == 1
        
        print(f"\n4. Database Storage:")
        print(f"   ✓ Matches saved: {saved_count}")
        
        # Step 5: Verify match retrieval
        user_matches = db.get_user_job_matches(test_user['id'], min_semantic_score=0)
        user_match = next((m for m in user_matches if m['job_id'] == test_job['job_id']), None)
        assert user_match is not None, f"Should find match with job_id={test_job['job_id']}"
        
        print(f"\n5. Match Retrieval:")
        print(f"   ✓ Match retrieved from database")
        print(f"   ✓ Semantic score: {user_match['semantic_score']}%")
        print(f"   ✓ Reasoning: {user_match['match_reasoning'][:50]}...")
        
        print("\n" + "="*60)
        print("✅ COMPLETE PIPELINE TEST PASSED")
        print("="*60 + "\n")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
