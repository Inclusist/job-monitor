#!/usr/bin/env python3
"""
Delete today's matches to allow re-running with fixed Claude analysis
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from datetime import date

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Check today's matches
cursor.execute("""
    SELECT COUNT(*) 
    FROM user_job_matches 
    WHERE user_id = %s 
    AND created_date::date = %s::date
""", (93, str(date.today())))

count = cursor.fetchone()[0]
print(f"📊 Found {count} matches from today (2026-01-09) for user 93")

if count == 0:
    print("✓ No matches to delete")
    cursor.close()
    conn.close()
    sys.exit(0)

# Confirm deletion
print(f"\n⚠️  This will delete {count} match records from today")
print("   You'll be able to re-run matching with the fixed Claude analysis")
response = input("\nProceed? (yes/no): ")

if response.lower() != 'yes':
    print("❌ Cancelled")
    cursor.close()
    conn.close()
    sys.exit(0)

# Delete
cursor.execute("""
    DELETE FROM user_job_matches 
    WHERE user_id = %s 
    AND created_date::date = %s::date
""", (93, str(date.today())))

deleted = cursor.rowcount
conn.commit()
cursor.close()
conn.close()

print(f"\n✅ Deleted {deleted} matches from today")
print("\n🚀 Now run matching from the web UI:")
print("   1. Go to Jobs page")
print("   2. Click 'Start New Match'")
print("   3. Claude analysis will work properly this time!")
