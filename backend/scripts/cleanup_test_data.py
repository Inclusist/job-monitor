#!/usr/bin/env python3
"""
Cleanup script for test data
Removes test users, CVs, and associated data from the database
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor


def cleanup_test_data():
    """Remove test data from database"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return 1
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Find test users
        cursor.execute("""
            SELECT id, email, name 
            FROM users 
            WHERE email LIKE '%@test.com' 
            OR email LIKE 'test_%'
            OR name LIKE '%Test%'
        """)
        test_users = cursor.fetchall()
        
        if not test_users:
            print("No test users found")
            return 0
        
        print(f"Found {len(test_users)} test users:")
        for user in test_users:
            print(f"  - {user['email']} (ID: {user['id']})")
        
        response = input("\nDelete these test users? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled")
            return 0
        
        deleted_count = 0
        for user in test_users:
            user_id = user['id']
            email = user['email']
            
            # Delete user_job_matches
            cursor.execute("DELETE FROM user_job_matches WHERE user_id = %s", (user_id,))
            matches_deleted = cursor.rowcount
            
            # Delete CV profiles
            cursor.execute("""
                DELETE FROM cv_profiles 
                WHERE cv_id IN (SELECT id FROM cvs WHERE user_id = %s)
            """, (user_id,))
            profiles_deleted = cursor.rowcount
            
            # Delete CVs
            cursor.execute("DELETE FROM cvs WHERE user_id = %s", (user_id,))
            cvs_deleted = cursor.rowcount
            
            # Delete user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            
            print(f"✓ Deleted {email}: {cvs_deleted} CVs, {profiles_deleted} profiles, {matches_deleted} matches")
            deleted_count += 1
        
        conn.commit()
        print(f"\n✓ Successfully deleted {deleted_count} test users and associated data")
        
        return 0
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    sys.exit(cleanup_test_data())
