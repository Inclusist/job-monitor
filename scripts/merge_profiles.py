
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def merge_profiles():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Target User and CV
    user_id = 93
    print(f"--- Merging Profiles for User {user_id} ---\n")
    
    # 1. Get Source Profiles
    # Profile 50 = Good Work History, Raw Analysis
    # Profile 57 = Good Competencies
    
    cur.execute("SELECT * FROM cv_profiles WHERE id = 50")
    old_profile = cur.fetchone()
    
    cur.execute("SELECT * FROM cv_profiles WHERE id = 57")
    new_profile = cur.fetchone()
    
    if not old_profile or not new_profile:
        print("Error: Could not find profiles 50 and 57")
        return

    print(f"Loaded Profile 50 (Old) and 57 (New)")
    
    # 2. Prepare Merged Data
    # Base is OLD profile (to keep work history, etc.)
    merged_data = dict(old_profile)
    
    # Overwrite Competencies from NEW profile
    competencies_src = new_profile['competencies']
    # Ensure it's a list
    if isinstance(competencies_src, str):
        competencies_src = json.loads(competencies_src)
    
    print(f"Injecting {len(competencies_src)} competencies from Profile 57")
    merged_data['competencies'] = json.dumps(competencies_src) # Store as string for JSONB insert if needed? 
    # Wait, save_cv_profile uses json.dumps. 
    # Here we are doing DIRECT INSERT. 
    # If column is JSONB, and we use psycopg2, we should pass LIST/DICT directly.
    # But existing data in DB seems to be DOUBLE ENCODED strings based on my debug script saying "Type: str".
    # So I should probably keep it consistent or fix it.
    # My "fix" in PostgresCVManager handles strings. So passing a string is "safe" for compatibility.
    
    # Parse Base Data from Old Profile Raw Analysis (which has everything)
    base_raw_str = old_profile['raw_analysis']
    if isinstance(base_raw_str, str):
        base_data = json.loads(base_raw_str)
    elif isinstance(base_raw_str, dict):
        base_data = base_raw_str
    else:
        print("Error: Old profile raw_analysis is neither str nor dict")
        return

    # Update Competencies in Base Data
    base_data['competencies'] = competencies_src
    
    # Map work_experience to work_history if needed
    if 'work_experience' in base_data and 'work_history' not in base_data:
        base_data['work_history'] = base_data['work_experience']

    # New Insert Logic (using correct columns from save_cv_profile)
    # cv_id, user_id, technical_skills, soft_skills, competencies, languages,
    # education, work_history, achievements, expertise_summary,
    # career_level, preferred_roles, industries, raw_analysis,
    # created_date, last_updated

    insert_query = """
        INSERT INTO cv_profiles (
            cv_id, user_id, technical_skills, soft_skills, competencies, languages,
            education, work_history, achievements, expertise_summary,
            career_level, preferred_roles, industries, raw_analysis,
            created_date, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """

    now = datetime.now()
    values = (
        new_profile['cv_id'], # Use CV ID from new profile (59 vs 58)
        user_id,
        json.dumps(base_data.get('technical_skills', [])),
        json.dumps(base_data.get('soft_skills', [])),
        json.dumps(competencies_src), # The NEW competencies
        json.dumps(base_data.get('languages', [])),
        json.dumps(base_data.get('education', [])),
        json.dumps(base_data.get('work_history', []) or base_data.get('work_experience', [])),
        json.dumps(base_data.get('achievements', []) or base_data.get('career_highlights', [])),
        base_data.get('expertise_summary', ''),
        base_data.get('career_level', ''),
        json.dumps(base_data.get('preferred_roles', [])),
        json.dumps(base_data.get('industries', [])),
        json.dumps(base_data), # Full merged Raw Analysis
        now, now
    )
    
    try:
        cur.execute(insert_query, values)
        new_id = cur.fetchone()['id']
        conn.commit()
        print(f"✅ Created Merged Profile ID: {new_id}")
        
        # Set as primary? Usually latest is primary logic in get_cv_profile
        # But we need to make sure this CV (59) is primary. It is already (from debug output).
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to merge: {e}")
        conn.close()
        return

    conn.close()

if __name__ == "__main__":
    merge_profiles()
