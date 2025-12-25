#!/usr/bin/env python3
"""
Fix Priority Migration Script

Corrects priority values in user_job_matches table based on claude_score.
Uses the same logic as the fixed claude_analyzer:
- High: score >= 85
- Medium: score 70-84
- Low: score < 70
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.database.postgres_operations import PostgresDatabase

def calculate_priority(score):
    """Calculate correct priority based on score"""
    if score >= 85:
        return 'high'
    elif score >= 70:
        return 'medium'
    else:
        return 'low'

def main():
    """Fix priorities in database"""
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env")
        return 1
    
    db = PostgresDatabase(db_url)
    
    print('='*80)
    print('PRIORITY FIX MIGRATION')
    print('='*80)
    
    # Get all jobs with claude scores
    query = '''
    SELECT user_id, job_id, claude_score, priority
    FROM user_job_matches
    WHERE claude_score IS NOT NULL
    ORDER BY claude_score DESC
    '''
    
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    jobs = cursor.fetchall()
    
    print(f'\nFound {len(jobs)} jobs with Claude scores')
    
    # Check which need fixing
    to_fix = []
    for user_id, job_id, score, current_priority in jobs:
        correct_priority = calculate_priority(score)
        if current_priority != correct_priority:
            to_fix.append((user_id, job_id, score, current_priority, correct_priority))
    
    if not to_fix:
        print('✅ All priorities are already correct!')
        db._return_connection(conn)
        db.close()
        return 0
    
    print(f'\n⚠️  Found {len(to_fix)} jobs with incorrect priority:')
    for user_id, job_id, score, old_pri, new_pri in to_fix:
        print(f'  Job {job_id} (user {user_id}): score={score}, "{old_pri}" → "{new_pri}"')
    
    # Ask for confirmation
    response = input(f'\nFix {len(to_fix)} priorities? (yes/no): ')
    if response.lower() != 'yes':
        print('Cancelled.')
        db._return_connection(conn)
        db.close()
        return 0
    
    # Apply fixes
    print('\nApplying fixes...')
    update_query = '''
    UPDATE user_job_matches
    SET priority = %s
    WHERE user_id = %s AND job_id = %s
    '''
    
    fixed_count = 0
    for user_id, job_id, score, old_pri, new_pri in to_fix:
        try:
            cursor.execute(update_query, (new_pri, user_id, job_id))
            conn.commit()
            fixed_count += 1
            print(f'  ✓ Fixed job {job_id}')
        except Exception as e:
            print(f'  ✗ Error fixing job {job_id}: {e}')
    
    db._return_connection(conn)
    db.close()
    
    print('\n' + '='*80)
    print(f'COMPLETE: Fixed {fixed_count}/{len(to_fix)} jobs')
    print('='*80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
