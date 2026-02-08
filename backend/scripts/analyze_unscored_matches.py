#!/usr/bin/env python3
"""
Analyze existing semantic matches that don't have Claude scores yet
Saves results after each batch to avoid connection timeouts
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer

load_dotenv()


def analyze_unscored_matches(user_id: int, min_semantic_score: int = 50, batch_size: int = 15, limit: int = 200):
    """
    Run Claude analysis on semantic matches that don't have Claude scores yet
    Saves results after each batch to avoid connection timeouts
    
    Args:
        user_id: User ID to analyze matches for
        min_semantic_score: Minimum semantic score to analyze (default: 50)
        batch_size: Number of jobs to process per batch (default: 15)
        limit: Maximum number of jobs to analyze in this run (default: 200)
    """
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"\n{'='*60}")
    print(f"Analyzing Unscored Matches - User {user_id}")
    print(f"Limit: {limit} jobs (preventing overload)")
    print(f"{'='*60}\n")
    
    # Initialize databases
    job_db = PostgresDatabase(db_url)
    cv_manager = PostgresCVManager(job_db.connection_pool)
    
    # Get user's primary CV and profile
    primary_cv = cv_manager.get_primary_cv(user_id)
    if not primary_cv:
        print("❌ No primary CV found")
        return
    
    profile = cv_manager.get_cv_profile(primary_cv['id'], include_full_text=False)
    if not profile:
        print("❌ CV profile not found")
        return
    
    user = cv_manager.get_user_by_id(user_id)
    
    # Get matches that have semantic scores but no Claude scores
    print(f"🔍 Finding top {limit} matches with semantic score ≥ {min_semantic_score}%...")
    
    with job_db.connection_pool.getconn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ujm.job_id, ujm.semantic_score, j.*
                FROM user_job_matches ujm
                JOIN jobs j ON ujm.job_id = j.id
                WHERE ujm.user_id = %s
                  AND ujm.semantic_score >= %s
                  AND ujm.claude_score IS NULL
                ORDER BY ujm.semantic_score DESC
                LIMIT %s
            """, (user_id, min_semantic_score, limit))
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
        job_db.connection_pool.putconn(conn)
    
    if not rows:
        print(f"✓ No unscored matches found (all matches with semantic ≥{min_semantic_score}% already have Claude scores)")
        return
    
    # Convert to job dictionaries
    jobs_to_analyze = []
    for row in rows:
        job = dict(zip(columns, row))
        jobs_to_analyze.append(job)
    
    print(f"📊 Found {len(jobs_to_analyze)} matches to analyze")
    print(f"   Semantic score range: {min(j['semantic_score'] for j in jobs_to_analyze)}% - {max(j['semantic_score'] for j in jobs_to_analyze)}%\n")
    
    # Initialize Claude analyzer
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        return
    
    try:
        analyzer = ClaudeJobAnalyzer(api_key=api_key, db=job_db, user_email=user.get('email', 'unknown'))
        analyzer.set_profile_from_cv(profile)
    except Exception as e:
        print(f"❌ Could not initialize Claude analyzer: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Process and save in batches
    print(f"🤖 Running Claude analysis in batches of {batch_size}...\n")
    
    import time
    t_start = time.time()
    total_analyzed = 0
    total_saved = 0
    
    # Process in chunks
    for batch_start in range(0, len(jobs_to_analyze), batch_size):
        batch_end = min(batch_start + batch_size, len(jobs_to_analyze))
        batch = jobs_to_analyze[batch_start:batch_end]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (len(jobs_to_analyze) + batch_size - 1) // batch_size
        
        print(f"\n🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} jobs)...")
        
        try:
            # Analyze this batch
            analyzed_batch = analyzer.analyze_batch(batch, batch_size=len(batch))
            total_analyzed += len(analyzed_batch)
            
            # Save immediately after analyzing
            print(f"   💾 Saving batch {batch_num} results to database...")
            
            claude_batch_updates = []
            jobs_updated = 0
            
            for job in analyzed_batch:
                # 1. Update JOB table with extracted competencies/skills (Critical Fix)
                if job.get('ai_competencies') or job.get('ai_key_skills'):
                    try:
                        with job_db.connection_pool.getconn() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""
                                    UPDATE jobs 
                                    SET ai_competencies = %s,
                                        ai_key_skills = %s
                                    WHERE id = %s
                                """, (
                                    job.get('ai_competencies', []),
                                    job.get('ai_key_skills', []),
                                    job['id']
                                ))
                                conn.commit()
                            job_db.connection_pool.putconn(conn)
                            jobs_updated += 1
                    except Exception as e:
                        print(f"      ⚠️ Failed to update job {job['id']} competencies: {e}")

                if 'match_score' in job:
                    # Convert lists to strings for database storage
                    key_alignments = job.get('key_alignments', [])
                    potential_gaps = job.get('potential_gaps', [])
                    
                    # Handle both list of strings and list of dicts
                    if key_alignments and isinstance(key_alignments[0], dict):
                        key_alignments = [str(item) for item in key_alignments]
                    if potential_gaps and isinstance(potential_gaps[0], dict):
                        potential_gaps = [str(item) for item in potential_gaps]
                    
                    claude_batch_updates.append({
                        'user_id': user_id,
                        'job_id': job['id'],
                        'claude_score': job['match_score'],
                        'priority': job.get('priority', 'medium'),
                        'match_reasoning': job.get('reasoning', ''),
                        'key_alignments': key_alignments,
                        'potential_gaps': potential_gaps
                    })
                    
                    print(f"      ✓ {job.get('title', 'Unknown')[:45]} - Claude: {job['match_score']}%")
            
            if jobs_updated > 0:
                print(f"      ✨ Updated competencies/skills for {jobs_updated} jobs")
            
            if claude_batch_updates:
                # Get a fresh connection for each save
                updated_count = job_db.add_user_job_matches_batch(claude_batch_updates)
                total_saved += updated_count
                print(f"   ✅ Saved {updated_count} analyses from batch {batch_num}")
            
        except Exception as e:
            print(f"   ❌ Error processing batch {batch_num}: {e}")
            import traceback
            traceback.print_exc()
            # Continue with next batch
            continue
    
    t_elapsed = time.time() - t_start
    
    print(f"\n{'='*60}")
    print(f"✅ Analysis complete!")
    print(f"   Jobs analyzed: {total_analyzed}")
    print(f"   Jobs saved: {total_saved}")
    print(f"   Time: {t_elapsed:.1f}s ({t_elapsed/60:.1f} min)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze unscored semantic matches with Claude (incremental save)')
    parser.add_argument('--user-id', type=int, required=True, help='User ID to analyze matches for')
    parser.add_argument('--min-score', type=int, default=50, help='Minimum semantic score (default: 50)')
    parser.add_argument('--batch-size', type=int, default=15, help='Batch size (default: 15)')
    parser.add_argument('--limit', type=int, default=200, help='Maximum jobs to process in this run (default: 200)')
    
    args = parser.parse_args()
    
    analyze_unscored_matches(args.user_id, args.min_score, args.batch_size, args.limit)
