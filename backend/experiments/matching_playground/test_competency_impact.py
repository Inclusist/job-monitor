
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import copy

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from src.analysis.claude_analyzer import ClaudeJobAnalyzer

load_dotenv()

def get_user_profile(user_id=93):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get Primary CV content
    query = """
        SELECT p.* 
        FROM cv_profiles p
        JOIN cvs c ON p.cv_id = c.id
        WHERE c.user_id = %s AND c.is_primary = 1
        ORDER BY p.created_date DESC LIMIT 1
    """
    cur.execute(query, (user_id,))
    profile = cur.fetchone()
    conn.close()
    
    if profile and isinstance(profile.get('raw_analysis'), str):
         try:
             profile['raw_analysis'] = json.loads(profile['raw_analysis'])
         except:
             profile['raw_analysis'] = {}
             
    return dict(profile) if profile else None

def main():
    print("🧪 Starting A/B Test for Symmetric Competency Matching...")
    
    # 1. Get Real User Profile
    real_profile = get_user_profile(93)
    if not real_profile:
        print("❌ User 93 profile not found.")
        return

    # Check if competencies exist
    competencies = real_profile.get('raw_analysis', {}).get('competencies') or real_profile.get('competencies')
    if not competencies:
        print("⚠️ No competencies found in profile. Did re-parsing finish?")
        return
        
    print(f"✅ Loaded Profile. Found {len(competencies)} extracted competencies.")

    # 2. Create a "Strategic Leadership" Job
    # This job focuses on CAPABILITIES (Hiring, Strategy) rather than just list of tools.
    # It deliberately omits some specific tools User might have, to verify if Competencies bridge the gap.
    test_job = {
        'title': 'VP of Data Engineering',
        'company': 'TechScale AI',
        'location': 'Berlin (Hybrid)',
        'description': """
        We are scaling our engineering organization and looking for a VP of Data.
        
        The ideal candidate is not just a manager, but a builder. You must have experience:
        1. **Recruiting and scaling** data teams from scratch across multiple geographies (Evidence of hiring 10+ people is required).
        2. **Driving Technical Strategy**: You will own the roadmap and architecture for our Data Lakehouse.
        3. **Stakeholder Management**: You must sit with Product and Sales leadership to align data initiatives with revenue goals.
        4. **Mentoring**: You will be responsible for growing Senior Engineers into Staff/Principal roles.
        
        This is a high-stakes role. We need someone who has done this before at a scaling startup.
        """,
        'ai_keywords': ['Leadership', 'Scaling', 'Recruiting', 'Strategy', 'Mentoring', 'Data Architecture'] + ['Hiring & Team Building', 'Strategic Leadership', 'People Management', 'Product Strategy'],
        'ai_core_responsibilities': """
        The ideal candidate is not just a manager, but a builder. You must have experience:
        1. Recruiting and scaling data teams from scratch across multiple geographies (Evidence of hiring 10+ people is required).
        2. Driving Technical Strategy: You will own the roadmap and architecture for our Data Lakehouse.
        3. Stakeholder Management: You must sit with Product and Sales leadership to align data initiatives with revenue goals.
        4. Mentoring: You will be responsible for growing Senior Engineers into Staff/Principal roles.
        """
    }
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    analyzer = ClaudeJobAnalyzer(api_key)

    # --- Run A: Baseline (No Competencies) ---
    print("\n🔹 Run A: Baseline (Skills Only, No Competencies)...")
    profile_baseline = copy.deepcopy(real_profile)
    # Strip competencies to simulate old state
    if 'competencies' in profile_baseline:
        del profile_baseline['competencies']
    if 'raw_analysis' in profile_baseline and 'competencies' in profile_baseline['raw_analysis']:
        del profile_baseline['raw_analysis']['competencies']
        
    analyzer.set_profile_from_cv(profile_baseline)
    result_a = analyzer.analyze_job(test_job)
    
    # --- Run B: Enhanced (With Competencies) ---
    print("\n🔹 Run B: Enhanced (Symmetric Competency Matching)...")
    analyzer.set_profile_from_cv(real_profile) # Full profile
    result_b = analyzer.analyze_job(test_job)

    # --- Comparison ---
    print("\n" + "="*50)
    print(f"⚖️  A/B TEST RESULTS: {test_job['title']}")
    print("="*50)
    
    print(f"\n[BASELINE SCORE]: {result_a['match_score']} ({result_a['priority']})")
    print(f"Reasoning: {result_a['reasoning']}")
    
    print(f"\n[ENHANCED SCORE]: {result_b['match_score']} ({result_b['priority']})")
    print(f"Reasoning: {result_b['reasoning']}")
    
    delta = result_b['match_score'] - result_a['match_score']
    print("\n" + "-"*50)
    if delta > 0:
        print(f"📈 IMPROVEMENT: +{delta} points")
        print("The Semantic/Competency layer successfully bridged the gap!")
    elif delta < 0:
        print(f"📉 REGRESSION: {delta} points")
    else:
        print("eq No Change in Score.")
        
if __name__ == "__main__":
    main()
