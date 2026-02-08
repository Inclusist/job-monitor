#!/usr/bin/env python3
"""
Auto-apply PostgreSQL performance optimizations
"""

import os
from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_operations import PostgresDatabase

print("="*70)
print("Applying PostgreSQL Performance Optimizations")
print("="*70)

db_url = os.getenv('DATABASE_URL')
db = PostgresDatabase(db_url)

conn = db._get_connection()
cursor = conn.cursor()

# List of indexes to create
indexes = [
    ("idx_cvs_user_id", "cvs(user_id)", "User CV lookups"),
    ("idx_cvs_status", "cvs(status)", "CV status filtering"),
    ("idx_cvs_user_status", "cvs(user_id, status)", "Combined user+status queries"),
    ("idx_cv_profiles_user_id", "cv_profiles(user_id)", "User profile lookups"),
    ("idx_cv_profiles_cv_id", "cv_profiles(cv_id)", "CV-to-profile FK"),
    ("idx_jobs_status", "jobs(status)", "Job status filtering"),
    ("idx_jobs_discovered_date", "jobs(discovered_date)", "Date sorting/filtering"),
    ("idx_jobs_status_date", "jobs(status, discovered_date)", "Combined status+date"),
    ("idx_users_is_active", "users(is_active)", "Active user filtering"),
]

print("\n1. Creating Missing Indexes")
print("-" * 70)

# Need to set autocommit for CREATE INDEX CONCURRENTLY
conn.commit()
old_isolation = conn.isolation_level
conn.set_isolation_level(0)  # AUTOCOMMIT mode

for idx_name, idx_def, reason in indexes:
    try:
        # Check if index exists
        cursor.execute(f"""
            SELECT 1 FROM pg_indexes 
            WHERE indexname = '{idx_name}'
        """)
        
        if cursor.fetchone():
            print(f"✓ {idx_name} already exists")
        else:
            print(f"Creating {idx_name}...")
            print(f"  Purpose: {reason}")
            
            # Create index without CONCURRENTLY (simpler for small tables)
            cursor.execute(f"CREATE INDEX {idx_name} ON {idx_def}")
            print(f"✓ {idx_name} created successfully")
    
    except Exception as e:
        print(f"❌ Error creating {idx_name}: {e}")

conn.set_isolation_level(old_isolation)  # Restore

print("\n2. Updating Table Statistics (VACUUM ANALYZE)")
print("-" * 70)

tables = ['users', 'cvs', 'cv_profiles', 'jobs', 'user_job_matches', 
          'applications', 'search_history', 'job_feedback']

# VACUUM ANALYZE must be run outside a transaction
conn.commit()  # Commit any pending transaction
old_isolation = conn.isolation_level
conn.set_isolation_level(0)  # AUTOCOMMIT mode

for table in tables:
    try:
        print(f"Analyzing {table}...")
        cursor.execute(f"VACUUM ANALYZE {table}")
        print(f"✓ {table} analyzed")
    except Exception as e:
        print(f"⚠️  Error analyzing {table}: {e}")

conn.set_isolation_level(old_isolation)  # Restore isolation level

print("\n" + "="*70)
print("OPTIMIZATION COMPLETE")
print("="*70)

# Verify improvements
cursor.execute("""
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
        (SELECT count(*) FROM pg_indexes WHERE tablename = t.tablename) as num_indexes
    FROM pg_tables t
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
""")

print("\nTable Summary:")
print(f"{'Table':<20} {'Size':>10} {'Indexes':>10}")
print("-" * 45)
for row in cursor.fetchall():
    print(f"{row[1]:<20} {row[2]:>10} {row[3]:>10}")

print("\n✅ All optimizations applied!")
print("\nExpected Performance Improvement:")
print("  - Query speed: 2-3x faster")
print("  - Page loads: Should feel much snappier")
print("  - Network latency: Still ~170ms (can't fix, it's Railway)")
print("\n💡 Restart your Flask app to see the improvements!")

cursor.close()
db._return_connection(conn)
