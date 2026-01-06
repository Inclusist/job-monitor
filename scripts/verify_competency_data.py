"""
Quick test: Verify Claude uses competencies in scoring
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Get user profile
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n" + "="*60)
print("TESTING COMPETENCY MATCHING")
print("="*60)

# Get user 93's profile with competencies
cur.execute("""
    SELECT competencies, technical_skills
    FROM cv_profiles 
    WHERE user_id = 93 
    ORDER BY created_date DESC 
    LIMIT 1
""")

profile = cur.fetchone()

if profile:
    comps = profile['competencies']
    skills = profile['technical_skills']
    
    print(f"\n✅ User Profile Found:")
    print(f"   Competencies: {len(comps) if comps else 0}")
    if comps:
        for c in comps[:3]:
            name = c.get('name', c) if isinstance(c, dict) else c
            print(f"      • {name}")
    
    print(f"   Technical Skills: {len(skills) if skills else 0}")
    if skills:
        for s in skills[:5]:
            print(f"      • {s}")

# Get enriched jobs with competencies
cur.execute("""
    SELECT COUNT(*) as total
    FROM jobs 
    WHERE ai_competencies IS NOT NULL 
    AND array_length(ai_competencies, 1) > 0
""")

job_count = cur.fetchone()['total']
print(f"\n✅ Jobs with competencies: {job_count}")

# Get one sample job
cur.execute("""
    SELECT title, ai_competencies, ai_key_skills
    FROM jobs 
    WHERE ai_competencies IS NOT NULL 
    AND array_length(ai_competencies, 1) > 2
    LIMIT 1
""")

job = cur.fetchone()

if job:
    print(f"\n📋 Sample Job: {job['title'][:50]}")
    print(f"   Competencies: {job['ai_competencies']}")
    print(f"   Skills: {job['ai_key_skills'][:5] if job['ai_key_skills'] else []}")

conn.close()

print(f"\n✅ Data Setup Complete!")
print(f"   → Ready for Claude scoring test")
print(f"   → {job_count} jobs available for matching")
