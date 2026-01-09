#!/usr/bin/env python3
"""
Filter jobs using semantic similarity (sentence transformers)
Compares stored jobs against user's CV profile to find relevant matches

Usage:
    python scripts/filter_jobs.py --threshold 0.5 --dry-run
    python scripts/filter_jobs.py --threshold 0.6 --production
    python scripts/filter_jobs.py --user-email user@example.com --threshold 0.55
"""

import sys
import os
import argparse
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.factory import get_database
from src.database.cv_operations import CVManager


def load_sentence_transformer():
    """Load sentence transformer model"""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("\n❌ Error: sentence-transformers package not installed")
        print("Install with: pip install sentence-transformers")
        sys.exit(1)
    
    print("📥 Loading TechWolf/JobBERT-v3 model...")
    # TechWolf/JobBERT-v3: Job-specialized model for semantic matching
    # Supports: EN, DE, ES, CN
    # Optimized for job title similarity and skills matching
    # Test results: "waaaaay better" for job matching (title-only)
    model = SentenceTransformer('TechWolf/JobBERT-v3')
    print("✅ Job-specialized model loaded")
    return model


def build_cv_text(profile: Dict) -> str:
    """
    Build comprehensive text representation of CV profile
    
    Args:
        profile: CV profile dictionary from database
        
    Returns:
        Text string for semantic encoding
    """
    parts = []
    
    # Expertise summary
    if profile.get('expertise_summary'):
        parts.append(profile['expertise_summary'])
    
    # Career highlights
    if profile.get('career_highlights'):
        highlights = profile['career_highlights']
        if isinstance(highlights, list):
            parts.extend(highlights)
        else:
            parts.append(str(highlights))
    
    # Technical skills
    if profile.get('technical_skills'):
        skills = profile['technical_skills']
        if isinstance(skills, list):
            parts.append("Technical skills: " + ", ".join(skills))
        else:
            parts.append("Technical skills: " + str(skills))
    
    # Soft skills
    if profile.get('soft_skills'):
        skills = profile['soft_skills']
        if isinstance(skills, list):
            parts.append("Soft skills: " + ", ".join(skills))
        else:
            parts.append("Soft skills: " + str(skills))
    
    # Work experience
    if profile.get('work_experience'):
        exp = profile['work_experience']
        if isinstance(exp, list):
            for job in exp[:5]:  # Top 5 roles
                if isinstance(job, dict):
                    title = job.get('title', '')
                    company = job.get('company', '')
                    desc = job.get('description', '')
                    parts.append(f"{title} at {company}: {desc}")
                else:
                    parts.append(str(job))
        else:
            parts.append(str(exp))
    
    # Education
    if profile.get('education'):
        edu = profile['education']
        if isinstance(edu, list):
            for degree in edu:
                if isinstance(degree, dict):
                    deg = degree.get('degree', '')
                    field = degree.get('field', '')
                    uni = degree.get('institution', '')
                    parts.append(f"{deg} in {field} from {uni}")
                else:
                    parts.append(str(degree))
        else:
            parts.append(str(edu))
    
    # Industries
    if profile.get('industries'):
        industries = profile['industries']
        if isinstance(industries, list):
            parts.append("Industries: " + ", ".join(industries))
        else:
            parts.append("Industries: " + str(industries))
    
    # Leadership experience
    if profile.get('leadership_experience'):
        leadership = profile['leadership_experience']
        if isinstance(leadership, list):
            parts.extend([str(item) for item in leadership])
        else:
            parts.append(str(leadership))
    
    return " ".join(parts)


def build_job_text(job: Dict) -> str:
    """
    Build simple text representation of job posting (title-only for speed)

    Args:
        job: Job dictionary from database

    Returns:
        Job title string for semantic encoding
    """
    # Title-only matching - 95% faster than full description
    # Claude analysis will handle detailed matching later
    return job.get('title', '')


def calculate_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    return float(np.dot(embedding1, embedding2) / 
                 (np.linalg.norm(embedding1) * np.linalg.norm(embedding2)))


def apply_keyword_boosts(base_score: float, job: Dict, config_keywords: List[str]) -> Tuple[float, List[str]]:
    """
    Apply keyword boosts to base similarity score
    
    Args:
        base_score: Base similarity score from semantic matching
        job: Job dictionary
        config_keywords: Keywords from config.yaml
        
    Returns:
        Tuple of (boosted_score, matched_keywords)
    """
    boosts = []
    matched_keywords = []
    
    job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    
    # Check for exact keyword matches
    for keyword in config_keywords:
        if keyword.lower() in job_text:
            matched_keywords.append(keyword)
            
            # Higher boost for title matches
            if keyword.lower() in job.get('title', '').lower():
                boosts.append(0.15)
            else:
                boosts.append(0.05)
    
    # Leadership keywords
    leadership_terms = ['lead', 'principal', 'senior', 'head of', 'manager', 'director', 'leiter']
    for term in leadership_terms:
        if term in job.get('title', '').lower():
            boosts.append(0.10)
            break
    
    # Apply boosts (max cumulative boost of 0.3)
    total_boost = min(sum(boosts), 0.3)
    boosted_score = min(base_score + total_boost, 1.0)
    
    return boosted_score, matched_keywords


def filter_jobs(threshold: float = 0.5, user_email: str = None, dry_run: bool = True):
    """
    Filter jobs using semantic similarity
    
    Args:
        threshold: Minimum similarity score (0-1)
        user_email: Specific user email, or None for single-user mode
        dry_run: If True, show results without updating database
    """
    print(f"\n{'='*60}")
    print("JOB FILTER - Semantic Similarity")
    print(f"{'='*60}")
    print(f"Threshold: {threshold}")
    print(f"Mode: {'DRY RUN (no database updates)' if dry_run else 'PRODUCTION (will update database)'}")
    print(f"{'='*60}\n")
    
    # Load model
    model = load_sentence_transformer()
    
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

    # First check if there are unmatched jobs
    conn = job_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count FROM jobs j
        LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = ?
        WHERE ujm.id IS NULL
    """, (user_id,))
    unmatched_count = cursor.fetchone()['count']
    cursor.close()
    if hasattr(job_db, '_return_connection'):
        job_db._return_connection(conn)
    else:
        conn.close()

    if unmatched_count == 0:
        print(f"ℹ️  No unmatched jobs found - all jobs already filtered for this user")
        print(f"💡 Run bulk_load_arbeitsagentur.py to fetch new jobs")
        return

    print(f"📊 Found {unmatched_count} unmatched jobs for user\n")

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
    
    # Build CV embedding
    print("\n📝 Building CV representation...")
    cv_text = build_cv_text(profile)
    print(f"   CV text length: {len(cv_text)} characters")
    cv_embedding = model.encode(cv_text, show_progress_bar=False)
    
    # Get unmatched jobs for this user
    print(f"🔍 Fetching {unmatched_count} unmatched jobs...\n")
    conn = job_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.* FROM jobs j
        LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = ?
        WHERE ujm.id IS NULL
        ORDER BY j.discovered_date DESC
    """, (user_id,))
    jobs = [dict(row) for row in cursor.fetchall()]
    if hasattr(job_db, '_return_connection'):
        job_db._return_connection(conn)
    else:
        conn.close()
    
    # Load config keywords for boosting
    try:
        import yaml
        config_path = Path(__file__).parent.parent / 'config.yaml'
        with open(config_path) as f:
            config = yaml.safe_load(f)
        config_keywords = config.get('search_config', {}).get('keywords', [])
    except Exception as e:
        print(f"⚠️  Could not load config.yaml: {e}")
        config_keywords = []
    
    # Process jobs
    filtered_count = 0
    results = []
    
    for i, job in enumerate(jobs, 1):
        # Build job embedding
        job_text = build_job_text(job)
        job_embedding = model.encode(job_text, show_progress_bar=False)
        
        # Calculate similarity
        base_similarity = calculate_similarity(cv_embedding, job_embedding)
        
        # Apply keyword boosts
        final_score, matched_keywords = apply_keyword_boosts(
            base_similarity, job, config_keywords
        )
        
        # Convert to 0-100 scale for database
        match_score = int(final_score * 100)
        
        # Store result
        result = {
            'job_id': job['id'],
            'external_id': job['job_id'],
            'title': job['title'],
            'company': job['company'],
            'location': job['location'],
            'base_similarity': base_similarity,
            'final_score': final_score,
            'match_score': match_score,
            'matched_keywords': matched_keywords,
            'passed_filter': final_score >= threshold
        }
        results.append(result)
        
        # Update database in production mode - write to user_job_matches
        if not dry_run and final_score >= threshold:
            job_db.add_user_job_match(
                user_id=user_id,
                job_id=job['id'],
                semantic_score=match_score,
                match_reasoning=f"Semantic similarity: {final_score:.3f} | Keywords: {', '.join(matched_keywords) if matched_keywords else 'None'}"
            )
        
        if final_score >= threshold:
            filtered_count += 1
        
        # Progress indicator
        if i % 20 == 0:
            print(f"   Processed {i}/{len(jobs)} jobs... ({filtered_count} matches so far)")
    
    # Sort by score
    results.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Display results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}\n")
    
    passed = [r for r in results if r['passed_filter']]
    failed = [r for r in results if not r['passed_filter']]
    
    print(f"✅ Passed filter (>= {threshold}): {len(passed)}")
    print(f"❌ Below threshold: {len(failed)}")
    print(f"📊 Filter rate: {len(passed)/len(results)*100:.1f}%\n")
    
    # Show top matches
    print(f"{'='*60}")
    print("TOP MATCHES")
    print(f"{'='*60}\n")
    
    for i, result in enumerate(passed[:20], 1):
        print(f"{i}. [{result['match_score']}%] {result['title']}")
        print(f"   {result['company']} | {result['location']}")
        print(f"   Similarity: {result['final_score']:.3f} (base: {result['base_similarity']:.3f})")
        if result['matched_keywords']:
            print(f"   Keywords: {', '.join(result['matched_keywords'])}")
        print()
    
    # Show distribution
    score_ranges = {
        '90-100': len([r for r in results if 90 <= r['match_score'] <= 100]),
        '80-89': len([r for r in results if 80 <= r['match_score'] < 90]),
        '70-79': len([r for r in results if 70 <= r['match_score'] < 80]),
        '60-69': len([r for r in results if 60 <= r['match_score'] < 70]),
        '50-59': len([r for r in results if 50 <= r['match_score'] < 60]),
        '<50': len([r for r in results if r['match_score'] < 50])
    }
    
    print(f"{'='*60}")
    print("SCORE DISTRIBUTION")
    print(f"{'='*60}")
    for range_name, count in score_ranges.items():
        bar = '█' * (count // 2)
        print(f"{range_name:8} | {bar} {count}")
    
    if dry_run:
        print(f"\n💡 This was a DRY RUN - no database updates made")
        print(f"💡 Run with --production to update match scores in database")
    else:
        print(f"\n✅ Added {len(passed)} job matches for user in database")
        # Update last filter run time
        cv_db.update_filter_run_time(user_id)
        print(f"✅ Updated last filter run time")
    
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Filter jobs using semantic similarity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with default threshold (0.5)
  python scripts/filter_jobs.py --dry-run

  # Production run with higher threshold
  python scripts/filter_jobs.py --threshold 0.6 --production

  # Filter for specific user
  python scripts/filter_jobs.py --user-email user@example.com --production
        """
    )
    
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.5,
        help='Minimum similarity score to pass filter (0.0-1.0). Default: 0.5'
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
        help='Show results without updating database (default)'
    )
    
    mode_group.add_argument(
        '--production',
        action='store_true',
        help='Update match scores in database'
    )
    
    args = parser.parse_args()
    
    # Validate threshold
    if not 0 <= args.threshold <= 1:
        print("❌ Error: threshold must be between 0 and 1")
        sys.exit(1)
    
    # Run filter
    try:
        filter_jobs(
            threshold=args.threshold,
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
