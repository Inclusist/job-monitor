
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Add project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.analysis.cv_analyzer import CVAnalyzer
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
    # Adjust path if relative
    if not os.path.exists(file_path):
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_path)
    
    print(f"📄 Processing CV: {file_path}")
    text, _ = CVParser.extract_text(file_path)
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    print("\n🤖 Running PRODUCTION CVAnalyzer (should use V2 logic)...")
    analyzer = CVAnalyzer(api_key, model="claude-3-haiku-20240307")
    result = analyzer.analyze_cv(text, "test@example.com")
    
    print("\n" + "="*60)
    print("EXTRACTION RESULTS")
    print("="*60)
    
    summary = result.get('semantic_summary')
    seniority = result.get('derived_seniority')
    domains = result.get('domain_expertise')
    role = result.get('extracted_role')
    
    print(f"Role: {role}")
    print(f"Seniority: {seniority}")
    print(f"Domains: {domains}")
    print(f"Summary Start: {summary[:100]}..." if summary else "None")
    
    if summary and seniority != 'Mid':
        print("\n✅ SUCCESS: Abstract fields extracted correctly!")
    else:
        print("\n❌ FAILURE: Abstract fields missing or default.")
        
    conn.close()

if __name__ == "__main__":
    main()
