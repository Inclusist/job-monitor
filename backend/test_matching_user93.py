#!/usr/bin/env python3
"""
Quick test to see if matching can run for user 93
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, 'src')

from database.postgres_operations import PostgresDatabase
from database.postgres_cv_operations import PostgresCVManager

# Test basic setup
print("Testing matching prerequisites for user 93...")
print("=" * 60)

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("❌ No DATABASE_URL")
    sys.exit(1)

print("✅ DATABASE_URL found")

# Initialize
job_db = PostgresDatabase(db_url)
cv_manager = PostgresCVManager(job_db.connection_pool)

user_id = 93

# Check CV
print(f"\nChecking user {user_id}...")
primary_cv = cv_manager.get_primary_cv(user_id)
if not primary_cv:
    print("❌ No primary CV")
    sys.exit(1)

print(f"✅ Primary CV: {primary_cv['file_name']}")

# Check profile
profile = cv_manager.get_cv_profile(primary_cv['id'], include_full_text=False)
if not profile:
    print("❌ No CV profile")
    sys.exit(1)

print(f"✅ CV Profile found")
print(f"   Skills: {len(profile.get('technical_skills', []))}")
print(f"   Competencies: {len(profile.get('competencies', []))}")

# Check should_refilter
should_filter, reason = cv_manager.should_refilter(user_id)
print(f"\nShould refilter: {should_filter}")
print(f"Reason: {reason}")

if should_filter:
    print("\n✅ All prerequisites met - matching should run!")
else:
    print(f"\n⚠️  Matching won't run: {reason}")

print("\nNow try importing matcher...")
try:
    from matching.matcher import run_background_matching
    print("✅ Matcher imported successfully")
except Exception as e:
    print(f"❌ Failed to import matcher: {e}")
    import traceback
    traceback.print_exc()
