import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n📊 Cross-Language Competency Quality Check\n")

# Get samples: 1 German, 1 English
cur.execute("""
    SELECT id, title, ai_job_language, ai_competencies, ai_key_skills
    FROM jobs 
    WHERE ai_competencies IS NOT NULL 
    AND array_length(ai_competencies, 1) > 0
    AND ai_job_language = 'de'
    LIMIT 1
""")
german_job = cur.fetchone()

cur.execute("""
    SELECT id, title, ai_job_language, ai_competencies, ai_key_skills
    FROM jobs 
    WHERE ai_competencies IS NOT NULL 
    AND array_length(ai_competencies, 1) > 0
    AND ai_job_language = 'en'
    LIMIT 1
""")
english_job = cur.fetchone()

# Display results
for label, job in [("🇩🇪 GERMAN JOB", german_job), ("🇬🇧 ENGLISH JOB", english_job)]:
    if job:
        print(f"\n{label}")
        print("-" * 60)
        print(f"Title: {job['title'][:60]}")
        print(f"\n✅ Competencies ({len(job['ai_competencies'])}):")
        for comp in job['ai_competencies']:
            print(f"   • {comp}")
        print(f"\n🔧 Skills ({len(job['ai_key_skills']) if job['ai_key_skills'] else 0}):")
        if job['ai_key_skills']:
            for skill in job['ai_key_skills'][:5]:
                print(f"   • {skill}")
    else:
        print(f"\n{label}: No sample found")

# Statistics by language
print("\n" + "="*60)
print("📈 EXTRACTION STATISTICS BY LANGUAGE")
print("="*60)

cur.execute("""
    SELECT 
        ai_job_language as lang,
        COUNT(*) as total,
        AVG(array_length(ai_competencies, 1)) as avg_comps,
        AVG(array_length(ai_key_skills, 1)) as avg_skills
    FROM jobs 
    WHERE ai_competencies IS NOT NULL
    GROUP BY ai_job_language
    ORDER BY total DESC
""")

stats = cur.fetchall()
for stat in stats:
    lang_name = {"de": "German 🇩🇪", "en": "English 🇬🇧", "fr": "French 🇫🇷"}.get(stat['lang'], stat['lang'])
    print(f"\n{lang_name}:")
    print(f"   Jobs Enriched: {stat['total']}")
    print(f"   Avg Competencies: {stat['avg_comps']:.1f}")
    print(f"   Avg Skills: {stat['avg_skills']:.1f}")

conn.close()
