import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Count jobs without competencies (or with source_type NULL - unenriched)
cur.execute("""
    SELECT COUNT(*) FROM jobs 
    WHERE ai_competencies IS NULL OR array_length(ai_competencies, 1) IS NULL
""")
unenriched = cur.fetchone()[0]

# Count total jobs
cur.execute("SELECT COUNT(*) FROM jobs")
total = cur.fetchone()[0]

print(f"\n📊 Job Enrichment Status:")
print(f"   Total Jobs: {total}")
print(f"   Unenriched: {unenriched}")
print(f"   Enriched: {total - unenriched}")
print(f"   Progress: {((total - unenriched) / total * 100):.1f}%")

cur.close()
conn.close()
