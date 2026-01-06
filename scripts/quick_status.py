import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM jobs WHERE ai_competencies IS NOT NULL AND array_length(ai_competencies, 1) > 0")
enriched = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM jobs")
total = cur.fetchone()[0]

print(f"\n📊 Job Enrichment Progress:")
print(f"   Enriched: {enriched}/{total} ({enriched/total*100:.1f}%)")
print(f"   Remaining: {total - enriched}")

conn.close()
