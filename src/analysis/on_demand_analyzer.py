"""
On-demand Claude analysis for a single job.
"""
import os
from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer

def analyze_job_on_demand(user_id: int, job_id: int) -> bool:
    """
    Run on-demand Claude analysis for a single job and user.
    
    Args:
        user_id: The ID of the user.
        job_id: The ID of the job to analyze.
        
    Returns:
        True if analysis was successful, False otherwise.
    """
    try:
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("❌ Database connection not configured.")
            return False

        job_db_inst = PostgresDatabase(db_url)
        cv_manager_inst = PostgresCVManager(job_db_inst.connection_pool)

        user = cv_manager_inst.get_user_by_id(user_id)
        if not user:
            print(f"❌ User with ID {user_id} not found.")
            return False

        primary_cv = cv_manager_inst.get_primary_cv(user_id)
        if not primary_cv:
            print(f"❌ No primary CV found for user {user_id}.")
            return False

        profile = cv_manager_inst.get_cv_profile(primary_cv['id'], include_full_text=False)
        if not profile:
            print(f"❌ CV profile not found for user {user_id}.")
            return False

        job = job_db_inst.get_job(job_id)
        if not job:
            print(f"❌ Job with ID {job_id} not found.")
            return False

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("⚠️  No ANTHROPIC_API_KEY found, skipping Claude analysis")
            return False
            
        analyzer = ClaudeJobAnalyzer(api_key=api_key, db=job_db_inst, user_email=user.get('email', 'unknown'))
        analyzer.set_profile(profile)

        print(f"\n🤖 Running on-demand Claude analysis for job {job_id} and user {user_id}...")
        analysis = analyzer.analyze_job(job)

        if analysis and 'match_score' in analysis:
            key_alignments = analysis.get('key_alignments', [])
            potential_gaps = analysis.get('potential_gaps', [])

            if key_alignments and isinstance(key_alignments[0], dict):
                key_alignments = [str(item) for item in key_alignments]
            if potential_gaps and isinstance(potential_gaps[0], dict):
                potential_gaps = [str(item) for item in potential_gaps]

            update_data = {
                'user_id': user_id,
                'job_id': job_id,
                'claude_score': analysis['match_score'],
                'priority': analysis.get('priority', 'medium'),
                'match_reasoning': analysis.get('reasoning', ''),
                'key_alignments': key_alignments,
                'potential_gaps': potential_gaps
            }
            
            job_db_inst.add_user_job_matches_batch([update_data])
            print(f"  ✓ {job.get('title', 'Unknown')[:50]} - Claude: {analysis['match_score']}")
            print("✓ On-demand Claude analysis complete.")
            return True
        else:
            print("❌ Claude analysis failed to produce a score.")
            return False

    except Exception as e:
        print(f"❌ Error in on-demand Claude analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
