"""
Test Claude Competency Scoring
Verify that the ClaudeJobAnalyzer is correctly using competency symmetry
"""
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from src.database.factory import get_cv_manager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer

load_dotenv()

# Initialize
cv_manager = get_cv_manager()
analyzer = ClaudeJobAnalyzer()

# Get user 93's primary CV profile
user_id = 93
profile = cv_manager.get_primary_profile(user_id)

if not profile:
    print("No profile found for user 93")
    exit(1)

print(f"\n{'='*60}")
print("CV PROFILE COMPETENCIES")
print(f"{'='*60}")
competencies = profile.get('competencies', [])
print(f"Found {len(competencies)} competencies:")
for comp in competencies:
    name = comp.get('name', comp) if isinstance(comp, dict) else comp
    print(f"  • {name}")

# Get a sample job with competencies
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

# Find a job with competencies that might match
cur.execute("""
    SELECT id, title, ai_competencies, ai_key_skills, ai_core_responsibilities
    FROM jobs 
    WHERE ai_competencies IS NOT NULL 
    AND array_length(ai_competencies, 1) > 0
    ORDER BY RANDOM()
    LIMIT 1
""")

job = dict(cur.fetchone())
conn.close()

print(f"\n{'='*60}")
print(f"TEST JOB: {job['title']}")
print(f"{'='*60}")
print(f"\nJob Competencies ({len(job['ai_competencies'])}):")
for comp in job['ai_competencies']:
    print(f"  • {comp}")

print(f"\nJob Skills ({len(job['ai_key_skills']) if job['ai_key_skills'] else 0}):")
if job['ai_key_skills']:
    for skill in job['ai_key_skills'][:5]:
        print(f"  • {skill}")

# Set profile and analyze
print(f"\n{'='*60}")
print("RUNNING CLAUDE ANALYSIS")
print(f"{'='*60}")

analyzer.set_profile_from_cv(profile)
result = analyzer.analyze_job(job)

print(f"\n📊 RESULTS:")
print(f"   Overall Score: {result.get('overall_score', 'N/A')}/100")
print(f"   Role Fit: {result.get('role_fit_score', 'N/A')}/10")
print(f"   Growth Potential: {result.get('growth_potential_score', 'N/A')}/10")

print(f"\n💡 Match Reasoning:")
reasoning = result.get('match_reasoning', 'No reasoning provided')
# Print first 500 chars
print(reasoning[:500] + "..." if len(reasoning) > 500 else reasoning)

print(f"\n🔍 Looking for competency mentions in reasoning...")
competency_keywords = ['competenc', 'leadership', 'strategic', 'management', 'stakeholder']
found_mentions = []
for keyword in competency_keywords:
    if keyword.lower() in reasoning.lower():
        found_mentions.append(keyword)

if found_mentions:
    print(f"✅ Found competency-related terms: {', '.join(found_mentions)}")
else:
    print("❌ No competency mentions found in reasoning")
