import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n--- Checking Job Competencies ---\n")

# Count jobs with competencies
cur.execute("SELECT COUNT(*) as total FROM jobs WHERE ai_competencies IS NOT NULL AND array_length(ai_competencies, 1) > 0")
count = cur.fetchone()['total']
print(f"Jobs with competencies: {count}")

# Sample a few
cur.execute("""
    SELECT id, title, ai_competencies, ai_key_skills 
    FROM jobs 
    WHERE ai_competencies IS NOT NULL 
    AND array_length(ai_competencies, 1) > 0
    LIMIT 3
""")

jobs = cur.fetchall()
for job in jobs:
    print(f"\nJob {job['id']}: {job['title'][:50]}...")
    print(f"  Competencies ({len(job['ai_competencies'])}): {job['ai_competencies']}")
    print(f"  Skills ({len(job['ai_key_skills']) if job['ai_key_skills'] else 0}): {job['ai_key_skills'][:5] if job['ai_key_skills'] else []}")

conn.close()
