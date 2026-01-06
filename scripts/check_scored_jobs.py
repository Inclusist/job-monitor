import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

# Check user 93's scored jobs
cur.execute("""
    SELECT j.id, j.title, j.ai_competencies, ujm.match_score
    FROM jobs j
    JOIN user_job_matches ujm ON j.id = ujm.job_id
    WHERE ujm.user_id = 93
    AND ujm.match_score IS NOT NULL
    ORDER BY ujm.match_score DESC
    LIMIT 10
""")

scored_jobs = cur.fetchall()

print(f"\n📊 User 93's Top Scored Jobs:\n")
print(f"Total scored jobs: {len(scored_jobs)}")

with_comps = 0
for job in scored_jobs:
    has_comps = job['ai_competencies'] and len(job['ai_competencies']) > 0
    if has_comps:
        with_comps += 1
    comp_str = f"✅ {len(job['ai_competencies'])} competencies" if has_comps else "❌ No competencies"
    print(f"\n{job['match_score']}/100 - {job['title'][:50]}")
    print(f"   {comp_str}")

print(f"\n📈 Summary: {with_comps}/{len(scored_jobs)} scored jobs have competency data")

if with_comps == 0:
    print("\n💡 None of your scored jobs have competencies yet!")
    print("   → We should re-run matching on the 781 enriched jobs")

conn.close()
