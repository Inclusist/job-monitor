"""
Check specific user's matching status
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

email = "tobias.schulzeheinrichs@gmail.com"

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Get user ID
cur.execute("SELECT id FROM users WHERE email = %s", (email,))
result = cur.fetchone()
if not result:
    print(f"❌ User not found: {email}")
    sys.exit(1)

user_id = result[0]
print(f"User ID: {user_id}")
print(f"Email: {email}")
print("=" * 60)

# Unmatched jobs
cur.execute("""
    SELECT COUNT(*) FROM jobs j
    LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = %s
    WHERE ujm.id IS NULL
""", (user_id,))
unmatched = cur.fetchone()[0]
print(f"\n📊 Unmatched jobs: {unmatched:,}")

# Existing matches
cur.execute("SELECT COUNT(*) FROM user_job_matches WHERE user_id = %s", (user_id,))
matched = cur.fetchone()[0]
print(f"✅ Matched jobs: {matched:,}")

# Check user profile
cur.execute("""
    SELECT 
        cv.id as cv_id,
        cv.file_name,
        p.work_arrangement_preference,
        p.preferred_work_locations
    FROM users u
    JOIN cvs cv ON u.id = cv.user_id AND cv.is_primary = 1
    LEFT JOIN cv_profiles p ON cv.id = p.cv_id
    WHERE u.id = %s
""", (user_id,))

profile = cur.fetchone()
if profile:
    print(f"\n📄 Primary CV: {profile[1]}")
    print(f"Work preference: {profile[2]}")
    print(f"Preferred locations: {profile[3]}")
else:
    print("\n⚠️  No primary CV found!")

# Check recent job dates
cur.execute("""
    SELECT 
        DATE(discovered_date) as date,
        COUNT(*) as count
    FROM jobs j
    LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = %s
    WHERE ujm.id IS NULL
    GROUP BY DATE(discovered_date)
    ORDER BY date DESC
    LIMIT 7
""", (user_id,))

print(f"\n📅 Unmatched jobs by date:")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]:,} jobs")

conn.close()
print("\n" + "=" * 60)
print(f"\n💡 With {unmatched:,} unmatched jobs, pre-filtering will take time.")
print(f"   Estimated: {unmatched * 0.5 / 60:.0f}-{unmatched * 1.0 / 60:.0f} minutes")
print(f"   This is normal for the first run after the backlog!")
