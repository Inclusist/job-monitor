#!/usr/bin/env python3
"""
Analyze filtered jobs using Claude AI
Takes jobs that passed semantic filtering and analyzes them with Claude

Usage:
    python scripts/analyze_jobs.py --min-score 50 --dry-run
    python scripts/analyze_jobs.py --min-score 60 --production
    python scripts/analyze_jobs.py --max-jobs 20 --production
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.factory import get_database
from src.database.cv_operations import CVManager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer


def analyze_jobs(min_score: int = 50, max_jobs: int = None, 
                 user_email: str = None, dry_run: bool = True):
    """
    Analyze filtered jobs with Claude
    
    Args:
        min_score: Minimum semantic similarity score to analyze
        max_jobs: Maximum number of jobs to analyze (for cost control)
        user_email: Specific user email, or None for single-user mode
        dry_run: If True, show results without updating database
    """
    print(f"\n{'='*60}")
    print("CLAUDE JOB ANALYZER")
    print(f"{'='*60}")
    print(f"Minimum score: {min_score}%")
    if max_jobs:
        print(f"Max jobs: {max_jobs}")
    print(f"Mode: {'DRY RUN (no database updates)' if dry_run else 'PRODUCTION (will update database)'}")
    print(f"{'='*60}\n")
    
    # Load environment
    load_dotenv()
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in .env file")
        return
    
    # Connect to databases
    job_db = get_database()  # Auto-detects SQLite or PostgreSQL
    cv_db = CVManager()
    
    # Get user and CV profile
    if user_email:
        user = cv_db.get_user_by_email(user_email)
        if not user:
            print(f"❌ User not found: {user_email}")
            return
        user_id = user['id']
    else:
        # Single-user mode: get first user
        conn = cv_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if not row:
            print("❌ No users found in database")
            print("💡 Upload a CV first via the web UI at /upload")
            return
        user_id = row['id']
    
    # Get primary CV
    cvs = cv_db.get_user_cvs(user_id)
    primary_cv = next((cv for cv in cvs if cv['is_primary']), None)
    
    if not primary_cv:
        if cvs:
            primary_cv = cvs[0]  # Use first CV if no primary
        else:
            print("❌ No CV found for user")
            print("💡 Upload a CV first via the web UI at /upload")
            return
    
    # Get CV profile
    profile = cv_db.get_cv_profile(primary_cv['id'], include_full_text=False)
    if not profile:
        print("❌ No CV profile found (CV may not be parsed yet)")
        print("💡 Upload and parse a CV first via the web UI")
        return
    
    print(f"✅ Found CV: {primary_cv['file_name']}")
    print(f"   Years experience: {profile.get('total_years_experience', 'N/A')}")
    print(f"   Technical skills: {len(profile.get('technical_skills', []))}")
    
    # Initialize Claude analyzer
    print(f"\n🤖 Initializing Claude analyzer...")
    analyzer = ClaudeJobAnalyzer(
        api_key=api_key,
        model="claude-3-5-haiku-20241022",  # Cost-effective model
        db=job_db,
        user_email=user_email or 'default@localhost'
    )
    analyzer.set_profile_from_cv(profile)
    print("✅ Claude analyzer ready")
    
    # Get filtered jobs from user_job_matches that haven't been analyzed by Claude yet
    # These are jobs with semantic_score >= min_score but claude_score is NULL
    jobs_to_analyze = job_db.get_user_job_matches(
        user_id=user_id,
        min_semantic_score=min_score,
        limit=max_jobs
    )
    
    # Filter to only jobs without Claude analysis yet
    jobs_to_analyze = [j for j in jobs_to_analyze if j.get('claude_score') is None]
    
    if not jobs_to_analyze:
        print(f"\n⚠️  No jobs found with semantic_score >= {min_score} that need Claude analysis")
        print("💡 Run filter_jobs.py first to score jobs")
        return
    
    print(f"\n📊 Found {len(jobs_to_analyze)} jobs to analyze\n")
    
    # Cost estimation
    # Claude Haiku: ~$0.25 per million input tokens, ~$1.25 per million output tokens
    # Rough estimate: ~2000 input tokens + 200 output tokens per job
    # = $0.0005 input + $0.00025 output = ~$0.00075 per job
    estimated_cost = len(jobs_to_analyze) * 0.001  # Conservative estimate
    print(f"💰 Estimated cost: ${estimated_cost:.2f} (Claude Haiku)")
    print(f"{'='*60}\n")
    
    if not dry_run:
        response = input("⚠️  This will consume Claude API credits. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled by user")
            return
        print()
    
    # Analyze jobs
    results = []
    total_cost = 0
    analyzed_count = 0
    
    for i, match in enumerate(jobs_to_analyze, 1):
        print(f"[{i}/{len(jobs_to_analyze)}] Analyzing: {match['title']}")
        print(f"          Company: {match['company']}")
        print(f"          Semantic score: {match['semantic_score']}%")
        
        if dry_run:
            # Simulate analysis
            print(f"          ➜ DRY RUN - would analyze with Claude\n")
            results.append({
                'job_id': match['job_id'],
                'title': match['title'],
                'company': match['company'],
                'semantic_score': match['semantic_score'],
                'claude_analysis': 'DRY RUN - not analyzed'
            })
        else:
            # Real Claude analysis
            try:
                # Build job dict for analyzer
                job = {
                    'title': match['title'],
                    'company': match['company'],
                    'location': match['location'],
                    'description': match['description'],
                    'url': match['url'],
                    'posted_date': match['posted_date'],
                    'salary': match['salary']
                }
                
                analysis = analyzer.analyze_job(job)
                
                # Update user_job_matches with Claude analysis
                job_db.add_user_job_match(
                    user_id=user_id,
                    job_id=match['job_id'],
                    claude_score=analysis['match_score'],
                    priority=analysis['priority'],
                    match_reasoning=analysis['reasoning'],
                    key_alignments=analysis['key_alignments'],
                    potential_gaps=analysis['potential_gaps']
                )
                
                print(f"          ✅ Claude score: {analysis['match_score']}% ({analysis['priority']} priority)")
                print(f"          📝 {analysis['reasoning'][:100]}...")
                print()
                
                results.append({
                    'job_id': match['job_id'],
                    'title': match['title'],
                    'company': match['company'],
                    'semantic_score': match['semantic_score'],
                    'claude_score': analysis['match_score'],
                    'priority': analysis['priority'],
                    'reasoning': analysis['reasoning']
                })
                
                # Rough cost tracking (very approximate)
                total_cost += 0.001
                
            except Exception as e:
                print(f"          ❌ Error: {e}\n")
                results.append({
                    'job_id': match['job_id'],
                    'title': match['title'],
                    'company': match['company'],
                    'error': str(e)
                })
    
    # Display results
    print(f"\n{'='*60}")
    print("ANALYSIS RESULTS")
    print(f"{'='*60}\n")
    
    if dry_run:
        print(f"✅ Would analyze {len(jobs_to_analyze)} jobs")
        print(f"💰 Estimated cost: ${estimated_cost:.2f}")
    else:
        successful = [r for r in results if 'claude_score' in r]
        failed = [r for r in results if 'error' in r]
        
        print(f"✅ Analyzed: {len(successful)} jobs")
        if failed:
            print(f"❌ Failed: {len(failed)} jobs")
        print(f"💰 Approximate cost: ${total_cost:.2f}")
        
        # Show top results
        if successful:
            print(f"\n{'='*60}")
            print("TOP MATCHES (by Claude score)")
            print(f"{'='*60}\n")
            
            sorted_results = sorted(successful, key=lambda x: x['claude_score'], reverse=True)
            for i, result in enumerate(sorted_results[:10], 1):
                print(f"{i}. [{result['claude_score']}%] {result['title']}")
                print(f"   {result['company']} | Priority: {result['priority']}")
                print(f"   Semantic: {result.get('semantic_score', 'N/A')}%")
                print(f"   {result['reasoning'][:120]}...")
                print()
    
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze filtered jobs with Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be analyzed
  python scripts/analyze_jobs.py --min-score 50 --dry-run

  # Analyze top 20 jobs with production updates
  python scripts/analyze_jobs.py --min-score 60 --max-jobs 20 --production

  # Analyze all jobs above 70% semantic score
  python scripts/analyze_jobs.py --min-score 70 --production
        """
    )
    
    parser.add_argument(
        '--min-score',
        type=int,
        default=50,
        help='Minimum semantic similarity score to analyze (0-100). Default: 50'
    )
    
    parser.add_argument(
        '--max-jobs',
        type=int,
        help='Maximum number of jobs to analyze (for cost control)'
    )
    
    parser.add_argument(
        '--user-email',
        type=str,
        help='User email (for multi-user setup). Default: first user'
    )
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Show what would be analyzed without calling Claude (default)'
    )
    
    mode_group.add_argument(
        '--production',
        action='store_true',
        help='Actually analyze with Claude and update database'
    )
    
    args = parser.parse_args()
    
    # Validate min_score
    if not 0 <= args.min_score <= 100:
        print("❌ Error: min-score must be between 0 and 100")
        sys.exit(1)
    
    # Run analyzer
    try:
        analyze_jobs(
            min_score=args.min_score,
            max_jobs=args.max_jobs,
            user_email=args.user_email,
            dry_run=not args.production
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
