#!/usr/bin/env python3
"""Check completeness of AI metadata fields in raw_jobs_test"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM raw_jobs_test')
total = cursor.fetchone()[0]

# Check completeness of text fields
fields = [
    ('ai_core_responsibilities', 'Core Responsibilities'),
    ('ai_requirements_summary', 'Requirements Summary'),
    ('ai_education_requirements', 'Education Requirements'),
    ('ai_job_language', 'Job Language'),
]

print('AI Metadata Field Coverage:')
print('=' * 80)
for field, label in fields:
    cursor.execute(f"""
        SELECT COUNT(*) FROM raw_jobs_test
        WHERE {field} IS NOT NULL AND {field} != ''
    """)
    count = cursor.fetchone()[0]
    percentage = (count / total * 100) if total > 0 else 0
    print(f'{label:30s}: {count:3d}/{total} ({percentage:5.1f}%)')

# Check array fields
array_fields = [
    ('ai_benefits', 'Benefits'),
    ('locations_derived', 'Locations'),
    ('cities_derived', 'Cities'),
    ('regions_derived', 'Regions'),
    ('countries_derived', 'Countries'),
]

print()
for field, label in array_fields:
    cursor.execute(f"""
        SELECT COUNT(*) FROM raw_jobs_test
        WHERE {field} IS NOT NULL AND array_length({field}, 1) > 0
    """)
    count = cursor.fetchone()[0]
    percentage = (count / total * 100) if total > 0 else 0
    print(f'{label:30s}: {count:3d}/{total} ({percentage:5.1f}%)')

# Check remote field
cursor.execute('SELECT COUNT(*) FROM raw_jobs_test WHERE remote = true')
remote_count = cursor.fetchone()[0]
print(f'\nRemote jobs (remote_derived): {remote_count}/{total} ({remote_count/total*100:.1f}%)')

cursor.close()
conn.close()
