#!/usr/bin/env python3
"""
Test Claude analysis performance on existing high-score matches
"""
import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer

load_dotenv()

def test_claude_analysis(user_id: int, limit: int = 20):
    """
    Test Claude analysis on existing high-score matches
    
    Args:
        user_id: User ID to test
        limit: Number of jobs to analyze (default 20)
    """
    print(f"\n{'='*80}")
    print(f"CLAUDE ANALYSIS PERFORMANCE TEST")
    print(f"Testing with {limit} high-score jobs")
    print(f"{'='*80}\n")
    
    db_url = os.getenv('DATABASE_URL')
    db = PostgresDatabase(db_url)
    cv_manager = PostgresCVManager(db.connection_pool)
    
    # Get user
    user = cv_manager.get_user_by_id(user_id)
    print(f"User: {user.get('email')} (ID: {user_id})")
    
    # Get high-score matches that haven't been Claude-analyzed
    matches = db.get_user_job_matches(user_id)
    high_score_matches = [m for m in matches if m.get('semantic_score', 0) >= 70 and m.get('claude_score') is None]
    
    print(f"High-score matches (>=70%) without Claude analysis: {len(high_score_matches)}")
    
    if len(high_score_matches) == 0:
        print("❌ No high-score matches to analyze. Run semantic matching first.")
        db.close()
        return
    
    # Limit to test set
    test_matches = high_score_matches[:limit]
    print(f"Testing with: {len(test_matches)} matches\n")
    
    # Initialize Claude analyzer
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ No ANTHROPIC_API_KEY found")
        db.close()
        return
    
    analyzer = ClaudeJobAnalyzer(api_key=api_key, db=db, user_email=user.get('email', 'unknown'))
    
    # Get user's CV
    cvs = cv_manager.get_user_cvs(user_id)
    if not cvs or len(cvs) == 0:
        print("❌ No CV found")
        db.close()
        return
    
    cv_data = cvs[0]
    
    # Set the user profile from CV
    analyzer.set_profile(cv_data)
    
    print("⏱️  Starting Claude analysis...\n")
    start_time = time.time()
    
    # Analyze each job
    results = []
    api_call_times = []
    parse_times = []
    
    for idx, match in enumerate(test_matches):
        job_table_id = match.get('job_table_id')
        if not job_table_id:
            print(f"  [{idx+1}/{len(test_matches)}] ⚠️  Match has no job_table_id")
            continue
            
        job = db.get_job_by_id(job_table_id)
        
        if not job:
            print(f"  [{idx+1}/{len(test_matches)}] ⚠️  Job {job_table_id} not found")
            continue
        
        print(f"  [{idx+1}/{len(test_matches)}] Analyzing job {job_table_id}: {job.get('title', 'N/A')[:50]}...")
        
        # Time the API call
        t_api_start = time.time()
        analysis = analyzer.analyze_job(job)
        t_api = time.time() - t_api_start
        api_call_times.append(t_api)
        
        if analysis:
            results.append(analysis)
            print(f"      ✓ Score: {analysis.get('match_score', 'N/A')}, Priority: {analysis.get('priority', 'N/A')} ({t_api:.2f}s)")
        else:
            print(f"      ✗ Analysis failed ({t_api:.2f}s)")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Update database with results (batch)
    if results:
        print(f"\n📝 Updating database with {len(results)} analyses...")
        t_db_start = time.time()
        
        updates = []
        for i, analysis in enumerate(results):
            job_table_id = test_matches[i].get('job_table_id')
            updates.append({
                'user_id': user_id,
                'job_id': test_matches[i]['job_id'],  # Use the hash job_id for the match table
                'claude_score': analysis.get('match_score'),
                'priority': analysis.get('priority'),
                'match_reasoning': analysis.get('reasoning', '')[:500]
            })
        
        db.add_user_job_matches_batch(updates)
        t_db = time.time() - t_db_start
        print(f"✓ Database updated ({t_db:.2f}s)")
    
    # Results
    print(f"\n{'='*80}")
    print(f"CLAUDE ANALYSIS RESULTS")
    print(f"{'='*80}")
    print(f"Total time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    print(f"Jobs analyzed: {len(test_matches)}")
    print(f"Successful: {len(results)}")
    print(f"Failed: {len(test_matches) - len(results)}")
    
    if api_call_times:
        avg_time = sum(api_call_times) / len(api_call_times)
        min_time = min(api_call_times)
        max_time = max(api_call_times)
        
        print(f"\n⏱️  API Call Timing:")
        print(f"  Average: {avg_time:.2f}s per job")
        print(f"  Min: {min_time:.2f}s")
        print(f"  Max: {max_time:.2f}s")
        print(f"  Total API time: {sum(api_call_times):.2f}s")
    
    # Extrapolate to full analysis
    if len(high_score_matches) > len(test_matches):
        estimated_full = (total_time / len(test_matches)) * len(high_score_matches)
        print(f"\n📈 Extrapolation to all {len(high_score_matches)} high-score matches:")
        print(f"  Estimated time: {estimated_full/60:.1f} minutes ({estimated_full:.0f} seconds)")
        
        if estimated_full > 600:  # 10 minutes
            print(f"  ⚠️  This is very slow! Expected: <5 minutes")
    
    db.close()

if __name__ == "__main__":
    user_id = 3
    limit = 20
    
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    
    test_claude_analysis(user_id, limit)
