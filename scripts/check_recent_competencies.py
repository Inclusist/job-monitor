#!/usr/bin/env python3
"""
Check if recent jobs have competencies extracted
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print("🔍 Checking recent Claude-scored jobs for competencies...")
print("="*80)

cursor.execute("""
    SELECT 
        j.id, j.title, j.company,
        ujm.claude_score,
        ujm.competency_mappings,
        ujm.skill_mappings,
        j.ai_competencies,
        j.ai_key_skills
    FROM user_job_matches ujm
    JOIN jobs j ON ujm.job_id = j.id
    WHERE ujm.user_id = 93
    AND ujm.created_date >= CURRENT_TIMESTAMP - INTERVAL '2 hours'
    AND ujm.claude_score IS NOT NULL
    ORDER BY ujm.created_date DESC
    LIMIT 10
""")

rows = cursor.fetchall()

if not rows:
    print("❌ No Claude-scored jobs found in last 2 hours")
    print("\nMaybe Claude analysis didn't run? Check Railway logs.")
else:
    for row in rows:
        print(f"\nJob {row['id']}: {row['title'][:45]}")
        print(f"  Company: {row['company']}")
        print(f"  Claude Score: {row['claude_score']}")
        
        # Check competencies
        comps = row['ai_competencies']
        if comps:
            if isinstance(comps, str):
                import json
                comps = json.loads(comps)
            comp_count = len(comps) if comps else 0
        else:
            comp_count = 0
        print(f"  Competencies extracted: {comp_count}")
        
        # Check skills
        skills = row['ai_key_skills']
        if skills:
            if isinstance(skills, str):
                import json
                skills = json.loads(skills)
            skill_count = len(skills) if skills else 0
        else:
            skill_count = 0
        print(f"  Skills extracted: {skill_count}")
        
        # Check mappings
        print(f"  Has competency_mappings: {row['competency_mappings'] is not None}")
        print(f"  Has skill_mappings: {row['skill_mappings'] is not None}")
        
cursor.close()
conn.close()

print("\n" + "="*80)
print("\n💡 If competencies = 0:")
print("   1. Competency extraction failed during matching")
print("   2. Check Railway logs for extraction errors")
print("   3. Jobs need to be re-enriched to extract competencies")
