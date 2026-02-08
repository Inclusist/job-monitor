
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def verify_db():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("\n--- Verifying Competencies Column ---")
    cur.execute("""
        SELECT id, user_id, competencies 
        FROM cv_profiles 
        WHERE user_id = 93 
        ORDER BY created_date DESC 
        LIMIT 1
    """)
    row = cur.fetchone()
    
    if row:
        print(f"Profile {row['id']} (User {row['user_id']})")
        comps = row['competencies']
        print(f"Column Structure: {type(comps)}")
        print(f"Content: {json.dumps(comps, indent=2)}")
        
        if comps and len(comps) > 0:
            print("✅ SUCCESS: Competencies found in dedicated column.")
        else:
            print("❌ FAILURE: Column is empty.")
    else:
        print("❌ No profile found for user.")

    conn.close()

if __name__ == "__main__":
    verify_db()
