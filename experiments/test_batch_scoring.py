#!/usr/bin/env python3
"""
Simplified test for batch scoring - just verify it works end-to-end
"""
import os, sys, json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.analysis.claude_analyzer import ClaudeJobAnalyzer

load_dotenv()

# Get user profile  
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

print("Loading profile...")
cur.execute("""
    SELECT p.* FROM cv_profiles p
    JOIN cvs c ON p.cv_id = c.id
    WHERE c.user_id = 93 AND c.is_primary = 1
    LIMIT 1
""")
profile = cur.fetchone()

if profile:
    profile = dict(profile)
    for f in ['technical_skills', 'soft_skills', 'competencies', 'work_history', 'raw_analysis']:
        if profile.get(f) and isinstance(profile[f], str):
            profile[f] = json.loads(profile[f])
    profile['work_experience'] = profile.get('work_history', [])
    print(f"✅ Loaded: {profile.get('name', 'Unknown')}")
else:
    print("❌ No profile")
    sys.exit(1)

# Get sample jobs
print("\nLoading jobs...")
cur.execute("""
    SELECT id, title, company, location, ai_key_skills, ai_keywords, 
           ai_core_responsibilities, ai_requirements_summary, 
           ai_experience_level, ai_work_arrangement, ai_competencies
    FROM jobs 
    WHERE ai_key_skills IS NOT NULL 
    LIMIT 5
""")
jobs = [dict(row) for row in cur.fetchall()]
cur.close()
conn.close()

print(f"✅ Loaded {len(jobs)} jobs")
for i, j in enumerate(jobs, 1):
    print(f"  {i}. {j['title']} - comps: {'Yes' if j.get('ai_competencies') else 'NO'}") 

# Test batch scoring
print("\n" + "="*60)
print("🚀 Running batch scoring...")
print("="*60)

analyzer = ClaudeJobAnalyzer(os.getenv('ANTHROPIC_API_KEY'), model="claude-3-5-haiku-20241022")
analyzer.set_profile_from_cv(profile)

try:
    scored = analyzer.analyze_batch(jobs, batch_size=5)
    
    print(f"\n✅ SUCCESS! Scored {len(scored)} jobs\n")
    for j in scored:
        print(f"{j['title']}: {j.get('match_score', 0)}/100 ({j.get('priority', '?')})")
        if j.get('ai_competencies'):
            print(f"  Comps: {', '.join(j['ai_competencies'][:3])}")
    
    print("\n💰 Estimated cost: $0.01-0.02 for batch vs $0.05 sequential")
    
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
