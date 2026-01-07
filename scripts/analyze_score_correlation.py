#!/usr/bin/env python3
"""
Analyze correlation between semantic scores and Claude scores
Helps optimize the threshold for which jobs to send to Claude
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.database.postgres_operations import PostgresDatabase
import matplotlib.pyplot as plt
import numpy as np

load_dotenv()


def analyze_score_correlation(user_id: int):
    """
    Analyze correlation between semantic and Claude scores
    
    Args:
        user_id: User ID to analyze
    """
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"\n{'='*60}")
    print(f"Score Correlation Analysis - User {user_id}")
    print(f"{'='*60}\n")
    
    # Initialize database
    job_db = PostgresDatabase(db_url)
    
    # Get all matches with both scores
    print("📊 Fetching matches with both semantic and Claude scores...")
    
    with job_db.connection_pool.getconn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    ujm.semantic_score,
                    ujm.claude_score,
                    ujm.priority,
                    j.title,
                    j.company
                FROM user_job_matches ujm
                JOIN jobs j ON ujm.job_id = j.id
                WHERE ujm.user_id = %s
                  AND ujm.semantic_score IS NOT NULL
                  AND ujm.claude_score IS NOT NULL
                ORDER BY ujm.semantic_score DESC
            """, (user_id,))
            
            rows = cur.fetchall()
            
        job_db.connection_pool.putconn(conn)
    
    if not rows:
        print("❌ No matches found with both scores")
        return
    
    print(f"✓ Found {len(rows)} matches with both scores\n")
    
    # Extract data
    semantic_scores = np.array([row[0] for row in rows])
    claude_scores = np.array([row[1] for row in rows])
    priorities = [row[2] for row in rows]
    
    # Calculate statistics
    correlation = np.corrcoef(semantic_scores, claude_scores)[0, 1]
    
    print(f"📈 CORRELATION ANALYSIS")
    print(f"{'='*60}")
    print(f"Correlation coefficient: {correlation:.3f}")
    print(f"  (1.0 = perfect positive, 0.0 = no correlation, -1.0 = perfect negative)\n")
    
    # Analyze by semantic score ranges
    print(f"📊 SCORE DISTRIBUTION BY SEMANTIC RANGE")
    print(f"{'='*60}")
    
    ranges = [
        (30, 40, "30-39%"),
        (40, 50, "40-49%"),
        (50, 60, "50-59%"),
        (60, 70, "60-69%"),
        (70, 80, "70-79%"),
        (80, 90, "80-89%"),
        (90, 100, "90-100%"),
    ]
    
    for min_score, max_score, label in ranges:
        mask = (semantic_scores >= min_score) & (semantic_scores < max_score)
        if mask.sum() > 0:
            avg_claude = claude_scores[mask].mean()
            min_claude = claude_scores[mask].min()
            max_claude = claude_scores[mask].max()
            count = mask.sum()
            
            # Count high-priority jobs
            high_priority = sum(1 for i, m in enumerate(mask) if m and priorities[i] == 'high')
            
            print(f"{label} semantic → Claude avg: {avg_claude:.1f}% (range: {min_claude}-{max_claude}%, n={count}, {high_priority} high priority)")
    
    # Analyze threshold optimization
    print(f"\n🎯 THRESHOLD OPTIMIZATION")
    print(f"{'='*60}")
    print("If we only Claude-analyze jobs with semantic score ≥ X:\n")
    
    thresholds = [30, 40, 50, 60, 70]
    for threshold in thresholds:
        mask = semantic_scores >= threshold
        jobs_analyzed = mask.sum()
        high_claude = (claude_scores[mask] >= 85).sum() if jobs_analyzed > 0 else 0
        medium_claude = ((claude_scores[mask] >= 70) & (claude_scores[mask] < 85)).sum() if jobs_analyzed > 0 else 0
        
        # Calculate what we'd miss
        missed_mask = semantic_scores < threshold
        missed_high = (claude_scores[missed_mask] >= 85).sum() if missed_mask.sum() > 0 else 0
        
        print(f"Threshold ≥{threshold}%:")
        print(f"  • Jobs to analyze: {jobs_analyzed} ({jobs_analyzed/len(rows)*100:.1f}%)")
        print(f"  • High matches found (≥85%): {high_claude}")
        print(f"  • Medium matches found (70-84%): {medium_claude}")
        print(f"  • High matches MISSED: {missed_high}")
        print()
    
    # Find outliers (high semantic, low Claude or vice versa)
    print(f"🔍 INTERESTING OUTLIERS")
    print(f"{'='*60}\n")
    
    print("High semantic (≥70%), Low Claude (<60%):")
    for i, (sem, claude, title, company) in enumerate(zip(semantic_scores, claude_scores, [r[3] for r in rows], [r[4] for r in rows])):
        if sem >= 70 and claude < 60:
            print(f"  • {title[:50]} @ {company[:30]}")
            print(f"    Semantic: {sem}%, Claude: {claude}%")
    
    print("\nLow semantic (<60%), High Claude (≥80%):")
    for i, (sem, claude, title, company) in enumerate(zip(semantic_scores, claude_scores, [r[3] for r in rows], [r[4] for r in rows])):
        if sem < 60 and claude >= 80:
            print(f"  • {title[:50]} @ {company[:30]}")
            print(f"    Semantic: {sem}%, Claude: {claude}%")
    
    # Create scatter plot
    print(f"\n📊 Generating scatter plot...")
    
    plt.figure(figsize=(10, 8))
    
    # Color by priority
    colors = {'high': 'red', 'medium': 'orange', 'low': 'blue'}
    for priority in ['low', 'medium', 'high']:
        mask = np.array([p == priority for p in priorities])
        if mask.sum() > 0:
            plt.scatter(semantic_scores[mask], claude_scores[mask], 
                       c=colors[priority], label=priority.capitalize(), alpha=0.6, s=50)
    
    # Add diagonal line (perfect correlation)
    plt.plot([0, 100], [0, 100], 'k--', alpha=0.3, label='Perfect correlation')
    
    # Add threshold lines
    plt.axvline(x=50, color='green', linestyle=':', alpha=0.5, label='Semantic threshold (50%)')
    plt.axhline(y=85, color='red', linestyle=':', alpha=0.5, label='High priority (85%)')
    
    plt.xlabel('Semantic Score (%)', fontsize=12)
    plt.ylabel('Claude Score (%)', fontsize=12)
    plt.title(f'Semantic vs Claude Score Correlation (r={correlation:.3f})', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 100)
    plt.ylim(0, 100)
    
    # Save plot
    output_path = project_root / 'score_correlation.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✓ Saved plot to: {output_path}")
    
    print(f"\n{'='*60}")
    print(f"✅ Analysis complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze semantic vs Claude score correlation')
    parser.add_argument('--user-id', type=int, required=True, help='User ID to analyze')
    
    args = parser.parse_args()
    
    analyze_score_correlation(args.user_id)
