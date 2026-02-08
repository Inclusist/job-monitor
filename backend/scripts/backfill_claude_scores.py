#!/usr/bin/env python3
"""
Backfill Claude scores for matches that only have semantic scores
Run this after fixing the Claude analysis bug to score previously unscored high matches
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database
from src.database.cv_operations import CVManager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer
from dotenv import load_dotenv

load_dotenv()

def backfill_claude_scores(user_id: int, min_semantic_score: int = 50):
    """
    Find matches with semantic scores but no Claude scores and score them
    
    Args:
        user_id: User ID to backfill
        min_semantic_score: Minimum semantic score to qualify for Claude analysis (default 50)
    """
    job_db = get_database()
    cv_manager = CVManager()
    
    # Get user
    user = cv_manager.get_user_by_id(user_id)
    if not user:
        print(f"❌ User {user_id} not found")
        return
    
    print(f"🔍 Finding matches needing Claude scores for user {user_id} ({user['email']})...")
    
    # Get matches with semantic scores but no Claude scores
    conn = job_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ujm.job_id, ujm.semantic_score, j.*
        FROM user_job_matches ujm
        JOIN jobs j ON ujm.job_id = j.id
        WHERE ujm.user_id = %s
        AND ujm.semantic_score >= %s
        AND ujm.claude_score IS NULL
        ORDER BY ujm.semantic_score DESC
    """, (user_id, min_semantic_score))
    
    rows = cursor.fetchall()
    jobs = []
    for row in rows:
        job_dict = dict(row)
        jobs.append(job_dict)
    
    cursor.close()
    job_db._return_connection(conn)
    
    if not jobs:
        print(f"✓ No matches need Claude scoring (all high matches already scored)")
        return
    
    print(f"📊 Found {len(jobs)} matches needing Claude analysis")
    print(f"   Semantic scores: {min([j['semantic_score'] for j in jobs])} - {max([j['semantic_score'] for j in jobs])}")
    
    # Get user's CV profile
    cvs = cv_manager.get_user_cvs(user_id)
    primary_cv = next((cv for cv in cvs if cv['is_primary']), cvs[0] if cvs else None)
    
    if not primary_cv:
        print("❌ No CV found for user")
        return
    
    profile = cv_manager.get_cv_profile(primary_cv['id'], include_full_text=False)
    if not profile:
        print("❌ No CV profile found")
        return
    
    # Initialize Claude analyzer
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ No ANTHROPIC_API_KEY found")
        return
    
    analyzer = ClaudeJobAnalyzer(api_key=api_key, db=job_db, user_email=user['email'])
    analyzer.set_profile_from_cv(profile)
    
    print(f"\n🤖 Running Claude analysis on {len(jobs)} jobs...")
    
    # Analyze in batch
    try:
        analyzed_jobs = analyzer.analyze_batch(jobs)
        print(f"✓ Analysis complete: {len(analyzed_jobs)} jobs")
    except Exception as e:
        print(f"❌ Batch analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Update database with Claude scores
    print(f"\n💾 Updating database with Claude scores...")
    updated = 0
    
    for job in analyzed_jobs:
        if 'match_score' in job:
            try:
                # Update the existing match record with Claude score
                conn = job_db._get_connection()
                cursor = conn.cursor()
                
                # Prepare alignments/gaps
                key_alignments = job.get('key_alignments', [])
                potential_gaps = job.get('potential_gaps', [])
                
                if key_alignments and isinstance(key_alignments[0], dict):
                    key_alignments = [str(item) for item in key_alignments]
                if potential_gaps and isinstance(potential_gaps[0], dict):
                    potential_gaps = [str(item) for item in potential_gaps]
                
                cursor.execute("""
                    UPDATE user_job_matches
                    SET claude_score = %s,
                        priority = %s,
                        match_reasoning = %s,
                        key_alignments = %s,
                        potential_gaps = %s
                    WHERE user_id = %s AND job_id = %s
                """, (
                    job['match_score'],
                    job.get('priority', 'medium'),
                    job.get('reasoning', ''),
                    key_alignments,
                    potential_gaps,
                    user_id,
                    job['id']
                ))
                
                conn.commit()
                cursor.close()
                job_db._return_connection(conn)
                
                print(f"  ✓ {job.get('title', 'Unknown')[:50]} - Claude: {job['match_score']}%")
                updated += 1
            except Exception as e:
                print(f"  ❌ Failed to update job {job['id']}: {e}")
    
    print(f"\n✅ Backfill complete: {updated}/{len(jobs)} matches updated with Claude scores")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backfill Claude scores for semantic-only matches')
    parser.add_argument('--user-id', type=int, default=93, help='User ID (default: 93)')
    parser.add_argument('--min-score', type=int, default=50, help='Minimum semantic score (default: 50)')
    args = parser.parse_args()
    
    backfill_claude_scores(args.user_id, args.min_score)
