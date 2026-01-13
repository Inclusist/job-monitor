"""
Diagnostic script to check user_job_matches status
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 60)
print("DATABASE DIAGNOSTIC: user_job_matches")
print("=" * 60)

# Total jobs
cur.execute("SELECT COUNT(*) FROM jobs")
total_jobs = cur.fetchone()[0]
print(f"\n📊 Total jobs in database: {total_jobs:,}")

# Jobs by date
cur.execute("""
    SELECT 
        DATE(discovered_date) as date,
        COUNT(*) as count
    FROM jobs
    WHERE discovered_date >= NOW() - INTERVAL '7 days'
    GROUP BY DATE(discovered_date)
    ORDER BY date DESC
    LIMIT 7
""")
print(f"\n📅 Jobs by date (last 7 days):")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]:,} jobs")

# Total match records
cur.execute("SELECT COUNT(*) FROM user_job_matches")
total_matches = cur.fetchone()[0]
print(f"\n🎯 Total match records: {total_matches:,}")

# Matches per user
cur.execute("""
    SELECT user_id, COUNT(*) as match_count
    FROM user_job_matches
    GROUP BY user_id
""")
print(f"\n👥 Matches by user:")
for row in cur.fetchall():
    print(f"   User {row[0]}: {row[1]:,} matches")

# Unmatched jobs per user
cur.execute("""
    SELECT 
        u.id as user_id,
        u.email,
        COUNT(j.id) as unmatched_jobs
    FROM users u
    CROSS JOIN jobs j
    LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = u.id
    WHERE ujm.id IS NULL
    GROUP BY u.id, u.email
""")
print(f"\n🔍 Unmatched jobs per user:")
for row in cur.fetchall():
    print(f"   User {row[0]} ({row[1]}): {row[2]:,} unmatched jobs")

# Check for recent matches
cur.execute("""
    SELECT 
        DATE(created_date) as date,
        COUNT(*) as count
    FROM user_job_matches
    WHERE created_date >= NOW() - INTERVAL '7 days'
    GROUP BY DATE(created_date)
    ORDER BY date DESC
""")
print(f"\n📈 Match records created (last 7 days):")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"   {row[0]}: {row[1]:,} matches created")
else:
    print("   ⚠️  No matches created in last 7 days!")

# Check match status distribution
cur.execute("""
    SELECT status, COUNT(*) as count
    FROM user_job_matches
    GROUP BY status
""")
print(f"\n📊 Match records by status:")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]:,}")

conn.close()
print("\n" + "=" * 60)
