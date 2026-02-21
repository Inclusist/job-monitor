
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.cv_analyzer import CVAnalyzer
from src.database.postgres_cv_operations import PostgresCVManager
from src.database.factory import get_database
from src.parsers.cv_parser import CVParser

load_dotenv()

def reparse_user_cv(user_id=93):
    print(f"🔄 Starting Re-parse for User {user_id} using Claude-3.5-Sonnet...")
    
    # 1. Setup DB
    db = get_database()
    cv_manager = PostgresCVManager(db.connection_pool)
    
    # 2. Get Primary CV
    primary_cv = cv_manager.get_primary_cv(user_id)
    if not primary_cv:
        print("❌ No primary CV found.")
        return

    print(f"📄 Found CV: {primary_cv['file_name']} (ID: {primary_cv['id']})")
    
    # 3. Read File Content
    # (In a real app, we'd read from S3 or disk. Here we query the 'full_text' from previous profile if file not on disk?)
    # Wait, we need the TEXT.
    # Let's check if the previous profile has full_text.
    old_profile = cv_manager.get_cv_profile(primary_cv['id'])
    cv_text = ""
    if old_profile and old_profile.get('raw_analysis'):
        # Sometimes full_text is saved
        pass
        
    # If we can't get text easily, we might fail. 
    # BUT, inspect_profile showed 'Raw Content'. 
    # Let's try to get it from the profile 'full_text' field if it exists? 
    # The 'cv_profiles' table doesn't have 'full_text' column, but maybe it's in raw_analysis?
    # Inspect schema showed raw_analysis is TEXT.
    
    # Let's assume we can get it from the file path if it's local?
    file_path = primary_cv['file_path']
    if os.path.exists(file_path):
        # Read text? No, it's PDF probably.
        # We need the extraction tool.
        # For this script, I will cheat and grab the 'full_text' from the 'raw_analysis' of the OLD profile if available.
        if old_profile:
             raw = old_profile.get('raw_analysis', {})
             if isinstance(raw, str): raw = json.loads(raw)
             cv_text = raw.get('full_text', '')
    
    print(f"📂 File Path from DB: {file_path}")
    if not cv_text or len(cv_text) < 50:
        print("⚠️ Text missing from DB. Attempting to read file using CVParser...")
        if os.path.exists(file_path):
             cv_text, status = CVParser.extract_text(file_path)
             if status == 'success':
                 print(f"✅ Extracted {len(cv_text)} chars using CVParser.")
             else:
                 print(f"❌ Extraction failed (Status: {status})")
        else:
             print(f"❌ File does not exist at path: {file_path}")
             # Final fallback: Look for file in 'data/cvs/...' relative to project root if path is relative
             # ... (Skipped for now, assuming absolute path or correct relative path)
             return

    print(f"📝 CV Text Length: {len(cv_text)} chars")

    # 4. Initialize Analyzer with POWERFUL Model
    api_key = os.getenv('ANTHROPIC_API_KEY')
    analyzer = CVAnalyzer(api_key, model="claude-haiku-4-5-20251001")
    
    # 5. Analyze
    print("🤖 Analyzing with Sonnet (may take 10-20s)...")
    new_profile = analyzer.analyze_cv(cv_text, "user_93@test.com")
    
    # 6. Save to DB
    # We must explicitly use save_cv_profile to populate the new column and the parsed fields
    print("💾 Saving new profile...")
    profile_id = cv_manager.save_cv_profile(primary_cv['id'], user_id, new_profile)
    
    # 7. Print Results
    comps = new_profile.get('competencies', [])
    print(f"\n✅ Analysis Complete! (Profile ID: {profile_id})")
    print(f"Extract Competencies: {len(comps)}")
    print(json.dumps(comps, indent=2))

if __name__ == "__main__":
    reparse_user_cv()
