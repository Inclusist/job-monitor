#!/usr/bin/env python3
"""Test first-time user matching with JSearch fetching"""
import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, '/Users/prabhu.ramachandran/job-monitor')

from src.matching.matcher import run_background_matching

load_dotenv()

print("\n" + "="*80)
print(f"FIRST-TIME USER TEST: User 87 (christina.ramachandran@gmail.com)")
print("This user has 15 keywords - would cause 30+ minute delay without fixes")
print("="*80 + "\n")

matching_status = {}

user_id = 87

# Delete existing matches to simulate first-time user
import psycopg2
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("DELETE FROM user_job_matches WHERE user_id = %s", (user_id,))
deleted = cur.rowcount
conn.commit()
cur.close()
conn.close()
print(f"✓ Deleted {deleted} existing matches for user 87\n")

print(f"⏱️  Starting matching with JSearch fetching...")
print("Expected: ~2-3 minutes with limits (was 30+ minutes without)")
print()

start = time.time()
run_background_matching(user_id, matching_status)
elapsed = time.time() - start

print("\n" + "="*80)
print(f"COMPLETE! Total time: {elapsed:.1f}s ({elapsed/60:.2f} minutes)")
print("="*80)

# Check results
from src.database.postgres_operations import PostgresDatabase
db = PostgresDatabase(os.getenv('DATABASE_URL'))
matches = db.get_user_job_matches(user_id)
print(f"\nMatches created: {len(matches)}")
if matches:
    high = len([m for m in matches if m.get('semantic_score', 0) >= 70])
    print(f"  High score (>=70%): {high}")
db.close()
