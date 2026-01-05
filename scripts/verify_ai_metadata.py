#!/usr/bin/env python3
"""Verify AI metadata was populated correctly in raw_jobs_test"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

# Total jobs
cursor.execute('SELECT COUNT(*) FROM raw_jobs_test')
total = cursor.fetchone()[0]
print(f'Total jobs in raw_jobs_test: {total}\n')

# Check how many have AI metadata
cursor.execute('SELECT COUNT(*) FROM raw_jobs_test WHERE ai_taxonomies_a IS NOT NULL AND array_length(ai_taxonomies_a, 1) > 0')
with_industries = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM raw_jobs_test WHERE ai_experience_level IS NOT NULL AND ai_experience_level != \'\'')
with_experience = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM raw_jobs_test WHERE ai_work_arrangement IS NOT NULL AND ai_work_arrangement != \'\'')
with_work_arrangement = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM raw_jobs_test WHERE ai_key_skills IS NOT NULL AND array_length(ai_key_skills, 1) > 0')
with_skills = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM raw_jobs_test WHERE ai_keywords IS NOT NULL AND array_length(ai_keywords, 1) > 0')
with_keywords = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM raw_jobs_test WHERE ai_employment_type IS NOT NULL AND array_length(ai_employment_type, 1) > 0')
with_employment_type = cursor.fetchone()[0]

print(f'Jobs with AI metadata:')
print(f'  Industries (ai_taxonomies_a): {with_industries}/{total}')
print(f'  Experience level: {with_experience}/{total}')
print(f'  Work arrangement: {with_work_arrangement}/{total}')
print(f'  Employment type: {with_employment_type}/{total}')
print(f'  Key skills: {with_skills}/{total}')
print(f'  Keywords: {with_keywords}/{total}')
print()

# Top industries
cursor.execute("""
    SELECT industry, COUNT(*) as count
    FROM raw_jobs_test, UNNEST(ai_taxonomies_a) as industry
    WHERE industry IS NOT NULL AND industry != ''
    GROUP BY industry
    ORDER BY count DESC
    LIMIT 10
""")

print('Top 10 Industries:')
print('-' * 60)
for industry, count in cursor.fetchall():
    print(f'  {industry}: {count}')
print()

# Experience levels
cursor.execute("""
    SELECT ai_experience_level, COUNT(*) as count
    FROM raw_jobs_test
    WHERE ai_experience_level IS NOT NULL AND ai_experience_level != ''
    GROUP BY ai_experience_level
    ORDER BY count DESC
""")

print('Experience Levels:')
print('-' * 60)
for level, count in cursor.fetchall():
    print(f'  {level}: {count}')
print()

# Work arrangements
cursor.execute("""
    SELECT ai_work_arrangement, COUNT(*) as count
    FROM raw_jobs_test
    WHERE ai_work_arrangement IS NOT NULL AND ai_work_arrangement != ''
    GROUP BY ai_work_arrangement
    ORDER BY count DESC
""")

print('Work Arrangements:')
print('-' * 60)
for arrangement, count in cursor.fetchall():
    print(f'  {arrangement}: {count}')
print()

# Employment types
cursor.execute("""
    SELECT emp_type, COUNT(*) as count
    FROM raw_jobs_test, UNNEST(ai_employment_type) as emp_type
    WHERE emp_type IS NOT NULL AND emp_type != ''
    GROUP BY emp_type
    ORDER BY count DESC
""")

print('Employment Types:')
print('-' * 60)
for emp_type, count in cursor.fetchall():
    print(f'  {emp_type}: {count}')
print()

# Top skills
cursor.execute("""
    SELECT skill, COUNT(*) as count
    FROM raw_jobs_test, UNNEST(ai_key_skills) as skill
    WHERE skill IS NOT NULL AND skill != ''
    GROUP BY skill
    ORDER BY count DESC
    LIMIT 15
""")

print('Top 15 Skills:')
print('-' * 60)
for skill, count in cursor.fetchall():
    print(f'  {skill}: {count}')

cursor.close()
conn.close()
