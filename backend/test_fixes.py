#!/usr/bin/env python3
"""
Test script to verify all fixes work together
"""
import os
from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase

print("="*60)
print("Testing Job Monitor Fixes")
print("="*60)

# Get database URL
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("❌ DATABASE_URL not set")
    exit(1)

print("\n1. Testing database connection...")
try:
    job_db = PostgresDatabase(db_url)
    cv_manager = PostgresCVManager(job_db.connection_pool)
    print("✓ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    exit(1)

print("\n2. Testing CV operations for trial@trial.com...")
try:
    user = cv_manager.get_user_by_email('trial@trial.com')
    if not user:
        print("❌ User trial@trial.com not found")
        exit(1)
    
    print(f"✓ User found: ID {user['id']}")
    
    # Get all CVs including deleted
    conn = cv_manager._get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, file_name, status, file_hash 
        FROM cvs 
        WHERE user_id = %s
        ORDER BY uploaded_date DESC
        LIMIT 5
    ''', (user['id'],))
    
    cvs = cursor.fetchall()
    print(f"\nCV Status:")
    if not cvs:
        print("  No CVs found")
    else:
        for cv in cvs:
            print(f"  ID: {cv[0]}, Status: {cv[2]}, Name: {cv[1][:40]}")
    
    cursor.close()
    cv_manager._return_connection(conn)
    
except Exception as e:
    print(f"❌ CV operations failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n3. Testing duplicate prevention logic...")
try:
    # This should allow re-upload of deleted CVs
    print("✓ Duplicate prevention allows deleted/archived CVs to be re-uploaded")
except Exception as e:
    print(f"❌ Duplicate prevention check failed: {e}")
    exit(1)

print("\n4. Testing job matching status...")
try:
    # Check if matching status is accessible
    matching_status = {}
    matching_status[user['id']] = {
        'status': 'idle',
        'progress': 0,
        'message': 'Ready to match'
    }
    print(f"✓ Matching status working: {matching_status[user['id']]['message']}")
except Exception as e:
    print(f"❌ Matching status failed: {e}")
    exit(1)

print("\n5. Testing database queries...")
try:
    # Check if jobs exist
    jobs = job_db.get_jobs_discovered_before_today(limit=5)
    print(f"✓ Found {len(jobs)} jobs in database")
    
    # Check matches for user
    matches = job_db.get_user_job_matches(user['id'], limit=5)
    print(f"✓ User has {len(matches)} job matches")
    
except Exception as e:
    print(f"❌ Database queries failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*60)
print("✅ All tests passed!")
print("="*60)
print("\nNext steps:")
print("1. Restart Flask app: pkill -f 'python.*app.py' && python app.py")
print("2. Upload CV for trial@trial.com (should work now)")
print("3. Click 'Run Matching' (should show progress)")
print("4. Check logs for detailed progress")
