"""
Test script to see how Claude would handle competency mapping
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from dotenv import load_dotenv
load_dotenv()

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from anthropic import Anthropic

# Get specific job and user
user_id = 93  # Replace with your user ID
job_id = 11333  # Replace with the job ID you're looking at

# Connect to DB
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

# Get job
cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
job = dict(cur.fetchone())

# Get user profile
cur.execute("""
    SELECT p.* 
    FROM cv_profiles p
    JOIN cvs c ON p.cv_id = c.id
    WHERE c.user_id = %s AND c.is_primary = 1
    ORDER BY p.created_date DESC LIMIT 1
""", (user_id,))
profile = dict(cur.fetchone())
conn.close()

# Parse JSON fields
for field in ['competencies', 'technical_skills']:
    if profile.get(field) and isinstance(profile[field], str):
        try:
            profile[field] = json.loads(profile[field])
        except:
            pass

# Extract competency names
comp_names = []
for comp in (profile.get('competencies') or []):
    if isinstance(comp, dict):
        comp_names.append(comp.get('name'))
    else:
        comp_names.append(str(comp))

skill_names = [str(s) for s in (profile.get('technical_skills') or [])]

print("=" * 60)
print(f"📄 Job: {job['title']} at {job['company']}")
print(f"👤 User Competencies: {', '.join(comp_names[:5])}...")
print(f"💻 User Skills: {', '.join(skill_names[:10])}...")
print(f"🎯 Job Competencies: {', '.join(job.get('ai_competencies', [])[:5])}...")
print(f"⚙️  Job Skills: {', '.join(job.get('ai_key_skills', [])[:10])}...")
print("=" * 60)

# Create test prompt for Claude with structured mapping request
prompt = f"""You are analyzing a job posting for a candidate.

JOB DETAILS:
Title: {job['title']}
Company: {job['company']}
Description: {job.get('description', '')[:1000]}...

REQUIRED COMPETENCIES: {', '.join(job.get('ai_competencies', []))}
REQUIRED SKILLS: {', '.join(job.get('ai_key_skills', []))}

CANDIDATE PROFILE:
Competencies: {', '.join(comp_names)}
Technical Skills: {', '.join(skill_names)}

Please provide a JSON response with the following structure:
{{
  "match_score": <0-100>,
  "competency_mappings": [
    {{
      "job_requirement": "End-to-End Model Development",
      "user_strength": "Strategic Leadership",
      "match_confidence": "high|medium|low",
      "explanation": "Brief explanation of why these align"
    }}
  ],
  "skill_mappings": [
    {{
      "job_skill": "Large Language Models (LLMs)",
      "user_skill": "AI",
      "match_confidence": "high|medium|low",
      "explanation": "Brief explanation"
    }}
  ]
}}

Focus on finding semantic connections even when exact wording differs.
"""

print("\n🤖 Calling Claude to test structured mapping...")
print("=" * 60)

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2000,
    temperature=0,
    messages=[{"role": "user", "content": prompt}]
)

result_text = response.content[0].text
print("\n📊 CLAUDE'S RESPONSE:\n")
print(result_text)

# Try to parse as JSON
try:
    result_json = json.loads(result_text)
    print("\n" + "=" * 60)
    print("✅ SUCCESSFULLY PARSED AS JSON")
    print(f"Match Score: {result_json.get('match_score')}")
    print(f"\nCompetency Mappings ({len(result_json.get('competency_mappings', []))}):")
    for mapping in result_json.get('competency_mappings', [])[:5]:
        print(f"  • {mapping['job_requirement']} ↔ {mapping['user_strength']}")
        print(f"    Confidence: {mapping.get('match_confidence', 'N/A')}")
    
    print(f"\nSkill Mappings ({len(result_json.get('skill_mappings', []))}):")
    for mapping in result_json.get('skill_mappings', [])[:10]:
        print(f"  • {mapping['job_skill']} ↔ {mapping['user_skill']}")
        print(f"    Confidence: {mapping.get('match_confidence', 'N/A')}")
except json.JSONDecodeError as e:
    print(f"\n⚠️  Could not parse as JSON: {e}")
