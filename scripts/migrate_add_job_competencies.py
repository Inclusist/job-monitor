import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("\n--- Adding ai_competencies column to jobs table ---\n")

try:
    # Add column if it doesn't exist
    cur.execute("""
        ALTER TABLE jobs 
        ADD COLUMN IF NOT EXISTS ai_competencies TEXT[]
    """)
    conn.commit()
    print("✅ Column added successfully")
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

cur.close()
conn.close()
