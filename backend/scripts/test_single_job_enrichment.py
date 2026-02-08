#!/usr/bin/env python3
"""
Test Single Job Enrichment

Extract and save competencies/skills for a single job using Claude analyzer.
Useful for debugging and verifying the enrichment pipeline works correctly.

Usage:
    python scripts/test_single_job_enrichment.py --job_id 21923 --user_id 93
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from src.analysis.claude_analyzer import ClaudeJobAnalyzer
from src.database.postgres_operations import PostgresDatabase

def get_job_details(job_id):
    """Fetch job from database"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM jobs
        WHERE id = %s
    """, (job_id,))

    job = cursor.fetchone()
    cursor.close()
    conn.close()

    return dict(job) if job else None

def get_user_cv_profile(user_id, db):
    """Get user's CV profile"""
    from src.database.postgres_cv_operations import PostgresCVManager
    cv_manager = PostgresCVManager(db.connection_pool)
    return cv_manager.get_primary_profile(user_id)

def main():
    parser = argparse.ArgumentParser(description='Test single job competency extraction')
    parser.add_argument('--job_id', type=int, required=True, help='Job ID to process')
    parser.add_argument('--user_id', type=int, required=True, help='User ID for profile context')
    args = parser.parse_args()

    print("=" * 70)
    print(f"🧪 TESTING JOB ENRICHMENT")
    print("=" * 70)
    print(f"Job ID: {args.job_id}")
    print(f"User ID: {args.user_id}")
    print()

    # Initialize database
    db = PostgresDatabase(os.getenv('DATABASE_URL'))

    # Step 1: Fetch job
    print("📄 Step 1: Fetching job from database...")
    job = get_job_details(args.job_id)

    if not job:
        print(f"❌ Job {args.job_id} not found!")
        return

    print(f"   ✓ Found: {job['title']}")
    print(f"   Company: {job.get('company', 'N/A')}")
    print(f"   Current ai_competencies: {job.get('ai_competencies')}")
    print(f"   Current ai_key_skills: {job.get('ai_key_skills')}")
    print()

    # Step 2: Get user profile
    print("👤 Step 2: Loading user CV profile...")
    cv_profile = get_user_cv_profile(args.user_id, db)

    if not cv_profile:
        print(f"❌ User {args.user_id} has no CV profile!")
        return

    print(f"   ✓ Profile loaded: {cv_profile.get('name', 'User')}")
    user_comps = cv_profile.get('competencies', [])
    user_skills = cv_profile.get('technical_skills', [])
    print(f"   User competencies: {len(user_comps)}")
    print(f"   User skills: {len(user_skills)}")
    print()

    # Step 3: Initialize Claude analyzer
    print("🤖 Step 3: Initializing Claude analyzer...")
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return

    analyzer = ClaudeJobAnalyzer(api_key=api_key, db=db)
    analyzer.set_profile_from_cv(cv_profile)
    print("   ✓ Analyzer ready")
    print()

    # Step 4: Extract competencies (if missing)
    print("🔍 Step 4: Extracting competencies and skills...")
    if not job.get('ai_competencies'):
        print("   Job missing competencies, extracting now...")

        # Use the batch extraction method with a single job
        extraction_map = analyzer.extract_competencies_batch([job])

        if extraction_map and 'job_1' in extraction_map:
            extracted = extraction_map['job_1']
            job['ai_competencies'] = extracted.get('competencies', [])
            job['ai_key_skills'] = extracted.get('skills', [])

            print(f"   ✓ Extracted {len(job['ai_competencies'])} competencies:")
            for comp in job['ai_competencies']:
                print(f"      - {comp}")
            print()
            print(f"   ✓ Extracted {len(job['ai_key_skills'])} skills:")
            for skill in job['ai_key_skills']:
                print(f"      - {skill}")
            print()
        else:
            print("   ❌ Extraction failed!")
            return
    else:
        print(f"   ✓ Job already has {len(job['ai_competencies'])} competencies")
        print(f"   ✓ Job already has {len(job.get('ai_key_skills', []))} skills")
        print()

    # Step 5: Analyze job match
    print("🎯 Step 5: Running full Claude analysis...")
    analysis = analyzer.analyze_job(job)

    print(f"   ✓ Match Score: {analysis.get('match_score')}%")
    print(f"   Priority: {analysis.get('priority')}")
    print(f"   Key Alignments: {len(analysis.get('key_alignments', []))}")
    print(f"   Potential Gaps: {len(analysis.get('potential_gaps', []))}")
    print()

    if analysis.get('competency_mappings'):
        print(f"   ✓ Competency Mappings: {len(analysis['competency_mappings'])}")
        for mapping in analysis['competency_mappings']:
            print(f"      • {mapping['job_requirement']} ← {mapping['user_strength']}")
            print(f"        Confidence: {mapping['match_confidence']}, {mapping['explanation']}")
        print()

    if analysis.get('skill_mappings'):
        print(f"   ✓ Skill Mappings: {len(analysis['skill_mappings'])}")
        for mapping in analysis['skill_mappings']:
            print(f"      • {mapping['job_skill']} ← {mapping['user_skill']}")
            print(f"        Confidence: {mapping['match_confidence']}, {mapping['explanation']}")
        print()

    # Step 6: Save to database
    print("💾 Step 6: Saving to database...")

    # Save competencies to jobs table
    if job.get('ai_competencies') or job.get('ai_key_skills'):
        print("   Updating jobs table with extracted competencies/skills...")
        jobs_to_update = [{
            'job_id': job['id'],
            'ai_competencies': job.get('ai_competencies', []),
            'ai_key_skills': job.get('ai_key_skills', [])
        }]
        db.update_jobs_competencies_batch(jobs_to_update)
        print("   ✓ Jobs table updated")

    # Save match analysis to user_job_matches table
    print("   Updating user_job_matches table with analysis...")
    match_data = [{
        'user_id': args.user_id,
        'job_id': job['id'],
        'claude_score': analysis.get('match_score'),
        'priority': analysis.get('priority', 'medium'),
        'match_reasoning': analysis.get('reasoning', ''),
        'key_alignments': analysis.get('key_alignments', []),
        'potential_gaps': analysis.get('potential_gaps', []),
        'competency_mappings': analysis.get('competency_mappings', []),
        'skill_mappings': analysis.get('skill_mappings', [])
    }]
    db.add_user_job_matches_batch(match_data)
    print("   ✓ User matches updated")
    print()

    # Step 7: Verify
    print("✅ Step 7: Verifying saved data...")
    updated_job = get_job_details(args.job_id)
    print(f"   ai_competencies: {len(updated_job.get('ai_competencies') or [])}")
    print(f"   ai_key_skills: {len(updated_job.get('ai_key_skills') or [])}")

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT claude_score, competency_mappings, skill_mappings
        FROM user_job_matches
        WHERE user_id = %s AND job_id = %s
    """, (args.user_id, args.job_id))
    match = cursor.fetchone()
    cursor.close()
    conn.close()

    if match:
        print(f"   claude_score: {match['claude_score']}")
        print(f"   competency_mappings: {len(match.get('competency_mappings') or [])}")
        print(f"   skill_mappings: {len(match.get('skill_mappings') or [])}")

    print()
    print("=" * 70)
    print("✅ TEST COMPLETE!")
    print("=" * 70)
    print()
    print(f"🌐 View job at: http://localhost:8080/jobs/{args.job_id}")
    print(f"   (or https://inclusist.com/jobs/{args.job_id})")

if __name__ == "__main__":
    main()
