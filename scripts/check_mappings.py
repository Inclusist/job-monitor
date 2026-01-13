"""
Check if competency_mappings are being saved to database
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import json

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Get a recent job for user 93
cur.execute("""
    SELECT 
        j.id, j.title, j.company,
        ujm.claude_score, ujm.semantic_score,
        ujm.competency_mappings,
        ujm.skill_mappings,
        j.ai_competencies,
        j.ai_key_skills
    FROM user_job_matches ujm
    JOIN jobs j ON ujm.job_id = j.id
    WHERE ujm.user_id = 93
    AND ujm.created_date >= '2026-01-08'
    ORDER BY ujm.created_date DESC
    LIMIT 10
""")

print("=" * 80)
print("RECENT JOBS FOR USER 93 (2026-01-08)")
print("=" * 80)

for row in cur.fetchall():
    job_id, title, company, claude, semantic, comp_map, skill_map, ai_comps, ai_skills = row
    
    print(f"\n📋 Job {job_id}: {title[:50]} at {company}")
    print(f"   Claude Score: {claude}")
    print(f"   Semantic Score: {semantic}")
    print(f"   Competency Mappings: {type(comp_map)} - {comp_map is not None}")
    if comp_map:
        if isinstance(comp_map, str):
            comp_map = json.loads(comp_map)
        print(f"      Count: {len(comp_map) if isinstance(comp_map, list) else 'N/A'}")
        if isinstance(comp_map, list) and comp_map:
            print(f"      Sample: {comp_map[0]}")
    
    print(f"   Skill Mappings: {type(skill_map)} - {skill_map is not None}")
    if skill_map:
        if isinstance(skill_map, str):
            skill_map = json.loads(skill_map)
        print(f"      Count: {len(skill_map) if isinstance(skill_map, list) else 'N/A'}")
    
    print(f"   AI Competencies: {len(ai_comps) if ai_comps else 0}")
    print(f"   AI Skills: {len(ai_skills) if ai_skills else 0}")

conn.close()
print("\n" + "=" * 80)
