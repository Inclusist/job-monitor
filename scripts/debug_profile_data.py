
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def debug_profiles():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    user_id = 93
    print(f"\n--- Debugging Profiles for User {user_id} ---\n")
    
    # 1. Check CVs
    print("CVs:")
    cur.execute("SELECT id, file_name, is_primary, uploaded_date FROM cvs WHERE user_id = %s", (user_id,))
    cvs = cur.fetchall()
    for cv in cvs:
        print(f"  CV {cv['id']}: {cv['file_name']} (Primary: {cv['is_primary']})")

    # 2. Check Profiles
    print("\nProfiles:")
    cur.execute("""
        SELECT id, cv_id, created_date, 
               technical_skills, soft_skills, competencies, work_history, raw_analysis 
        FROM (
            SELECT *, 
                   jsonb_array_length(CASE WHEN technical_skills IS NULL OR technical_skills = 'null' THEN '[]'::jsonb ELSE technical_skills::jsonb END) as tech_count
            FROM cv_profiles 
            WHERE user_id = %s
        ) sub
        ORDER BY created_date DESC
    """, (user_id,))
    
    profiles = cur.fetchall()
    for p in profiles:
        # manual count
        t_skills = p['technical_skills']
        c_skills = p['competencies']
        w_hist = p['work_history']
        raw = p['raw_analysis']
        
        t_len = len(json.loads(t_skills)) if t_skills and isinstance(t_skills, str) else 0
        
        # Check Work History
        w_len = 0
        if w_hist:
            if isinstance(w_hist, list): w_len = len(w_hist)
            elif isinstance(w_hist, str): w_len = len(json.loads(w_hist))
        
        # Check Raw Analysis
        raw_type = type(raw)
        raw_keys = list(raw.keys()) if isinstance(raw, dict) else "Not a dict"

        val_type = type(p['competencies'])
        print(f"  Profile {p['id']} (CV {p['cv_id']}): Tech={t_len}, Comp={len(c_skills) if isinstance(c_skills, list) else 0}, Work={w_len}")
        print(f"     Raw Analysis Type: {raw_type} Keys: {str(raw_keys)[:50]}...")
        if w_len == 0:
             print(f"     WARNING: Work History is empty/null. Value: {str(w_hist)[:50]}...")

    conn.close()

if __name__ == "__main__":
    debug_profiles()
