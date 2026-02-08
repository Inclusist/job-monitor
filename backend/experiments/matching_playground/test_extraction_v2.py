
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Add project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.analysis.cv_analyzer import CVAnalyzer
from src.analysis.cv_analyzer_v2 import CVAnalyzerV2
from src.parsers.cv_parser import CVParser

load_dotenv()

USER_ID = 93

def get_db_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def main():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Get Primary CV path
    cur.execute("SELECT * FROM cvs WHERE user_id = %s AND is_primary = 1", (USER_ID,))
    cv = cur.fetchone()
    
    if not cv:
        print("No primary CV found.")
        return

    file_path = cv['file_path']
    # Adjust path if relative from project root
    if not os.path.exists(file_path):
        # Try prepending project root
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_path)
    
    print(f"📄 Processing CV: {file_path}")
    
    # 2. Extract Text
    text, _ = CVParser.extract_text(file_path)
    if not text:
        print("Failed to extract text.")
        return
        
    print(f"   (Text length: {len(text)} chars)")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    # 3. Analyze V1 (Old)
    print("\n🤖 Running V1 Analyzer (Haiku)...")
    v1 = CVAnalyzer(api_key)
    res_v1 = v1.analyze_cv(text, "test@example.com")
    
    # 4. Analyze V2 (New)
    print("🧠 Running V2 Analyzer (Sonnet)...")
    v2 = CVAnalyzerV2(api_key)
    res_v2 = v2.analyze_cv(text, "test@example.com")
    
    # 5. Compare
    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80)
    
    print(f"\n[{'OLD (V1)':<30}] vs [{'NEW (V2)':<30}]")
    print("-" * 65)
    
    print(f"ROLE INFERRED:")
    print(f"V1: {res_v1.get('desired_job_titles', ['?'])[0] if res_v1.get('desired_job_titles') else 'None'}")
    print(f"V2: {res_v2.get('extracted_role')} (Derived Seniority: {res_v2.get('derived_seniority')})")
    
    print(f"\nDOMAINS:")
    print(f"V1: {res_v1.get('industries')}")
    print(f"V2: {res_v2.get('domain_expertise')}")
    
    print(f"\nSUMMARY:")
    print(f"🔴 V1 (Standard):")
    print(f"{res_v1.get('expertise_summary')}")
    print(f"\n🟢 V2 (Semantic):")
    print(f"{res_v2.get('semantic_summary')}")
    
    print(f"\nKEYWORDS FOR MATCHING:")
    print(f"V2 Abstract: {res_v2.get('search_keywords_abstract')}")
    
    conn.close()

if __name__ == "__main__":
    main()
