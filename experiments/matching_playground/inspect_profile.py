
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

USER_ID = 93

def main():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get Primary CV content
    query = """
        SELECT p.* 
        FROM cv_profiles p
        JOIN cvs c ON p.cv_id = c.id
        WHERE c.user_id = %s AND c.is_primary = 1
    """
    cur.execute(query, (USER_ID,))
    profile = cur.fetchone()
    
    if not profile:
        print("No profile found.")
        return
        
    print(f"Profile ID: {profile['id']}")
    
    raw = profile.get('raw_analysis')
    print(f"Raw Analysis Type: {type(raw)}")
    
    if isinstance(raw, str):
        print(f"Raw Content (first 500 chars): {raw[:500]}")
        try:
            data = json.loads(raw)
            print(f"Parsed Data Type: {type(data)}")
            if isinstance(data, str):
                print("Data is a string, trying double-decode...")
                try:
                    data = json.loads(data)
                except:
                    pass
        except:
            print("Failed to parse raw string.")
            data = {}
    elif isinstance(raw, dict):
        print("Raw is already dict.")
        data = raw
    else:
        print("Raw is None or unknown.")
        data = {}
        
    print("\n--- Abstract Fields ---")
    print(f"Role: {data.get('extracted_role')}")
    print(f"Seniority: {data.get('derived_seniority')}")
    print(f"Domains: {data.get('domain_expertise')}")
    print(f"Competencies: {json.dumps(data.get('competencies', []), indent=2)}")
    print(f"Summary: {str(data.get('semantic_summary'))[:100]}...")
    
    conn.close()

if __name__ == "__main__":
    main()
