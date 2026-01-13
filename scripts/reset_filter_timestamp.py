#!/usr/bin/env python3
"""
Reset last_filter_run timestamp to allow re-running matching
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Reset last_filter_run to yesterday
cursor.execute("""
    UPDATE users 
    SET last_filter_run = CURRENT_DATE - INTERVAL '1 day'
    WHERE id = 93
    RETURNING last_filter_run
""")

new_time = cursor.fetchone()[0]
conn.commit()
cursor.close()
conn.close()

print(f"✅ Reset last_filter_run to: {new_time}")
print("\n🚀 Now you can run matching from the web UI!")
print("   It will process all unmatched jobs with the fixed Claude code")
