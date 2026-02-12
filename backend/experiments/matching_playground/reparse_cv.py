
import os
import sys
import json
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# Add project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.postgres_cv_operations import PostgresCVManager
from src.parsers.cv_parser import CVParser
from src.analysis.cv_analyzer import CVAnalyzer
from src.cv.cv_handler import CVHandler

load_dotenv()

USER_ID = 93

def main():
    print(f"🔄 Starting CV Re-parsing for User {USER_ID}...")
    
    # Setup components with Postgres
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 1, os.getenv('DATABASE_URL'))
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    # Use PostgresCVManager instead of (SQLite) CVManager
    cv_manager = PostgresCVManager(db_pool)
    parser = CVParser()
    # Use Haiku with our new prompted logic
    analyzer = CVAnalyzer(os.getenv('ANTHROPIC_API_KEY'), model="claude-3-5-haiku-20241022")
    handler = CVHandler(cv_manager, parser, analyzer)
    
    # Get Primary CV
    user_cvs = cv_manager.get_user_cvs(USER_ID)
    primary_cv = next((cv for cv in user_cvs if cv.get('is_primary')), None)
    
    if not primary_cv:
        print("❌ No primary CV found")
        return
        
    print(f"📄 Found Primary CV: {primary_cv['file_name']} (ID: {primary_cv['id']})")
    
    # Reparse using handler
    print("⏳ Reparsing... (this calls Claude)")
    result = handler.reparse_cv(primary_cv['id'])
    
    if result['success']:
        print("✅ CV Reparsed Successfully!")
        
        # Verify new profile
        profile = cv_manager.get_cv_profile(primary_cv['id'])
        print("\n--- New Profile Data (From DB) ---")
        
        # Access raw analysis if columns not yet in DB schema or check abstract fields
        extracted_role = profile.get('extracted_role')
        seniority = profile.get('derived_seniority') 
        domains = profile.get('domain_expertise')
        
        # If these are None, check if they are inside 'raw_analysis' (if stored as json)
        # PostgresCVManager might handle this differently, let's just print top-level first
        print(f"Role: {extracted_role}")
        print(f"Seniority: {seniority}")
        print(f"Domains: {domains}")
        
        if not extracted_role and profile.get('raw_analysis'):
             raw = profile['raw_analysis']
             if isinstance(raw, str):
                 import json
                 raw = json.loads(raw)
             print(f"\n[Found in Raw Analysis]:")
             print(f"Role: {raw.get('extracted_role')}")
             print(f"Seniority: {raw.get('derived_seniority')}")
             print(f"Domains: {raw.get('domain_expertise')}")
             
        print("------------------------")
    else:
        print(f"❌ Failed: {result.get('message')}")
        
    db_pool.closeall()

if __name__ == "__main__":
    main()
