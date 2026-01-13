"""
Debug script to test semantic matching with real job and profile data
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import get_database
from src.analysis.semantic_matcher import get_semantic_matcher

# Get database
db = get_database()
cv_manager = PostgresCVManager(db.connection_pool)

# Get user profile
user_id = 93  # Adjust to your user ID
profile = cv_manager.get_primary_profile(user_id)

if not profile:
    print("❌ No profile found")
    sys.exit(1)

print(f"✓ Profile found")
print(f"  Competencies: {len(profile.get('competencies', []))} items")
print(f"  Technical Skills: {len(profile.get('technical_skills', []))} items")

# Show some competencies
comps = profile.get('competencies', [])[:5]
skills = profile.get('technical_skills', [])[:10]
print(f"\n📋 Sample Competencies:")
for c in comps:
    print(f"  - {c}")

print(f"\n💻 Sample Technical Skills:")
for s in skills:
    print(f"  - {s}")

# Test semantic matcher
print(f"\n🧪 Testing Semantic Matcher...")
matcher = get_semantic_matcher()

# Test cases
test_job_comps = [
    "End-to-End Model Development",
    "Technical Leadership",
    "Strategic Planning",
    "Team Management"
]

print(f"\n🎯 Testing competency matches:")
for job_comp in test_job_comps:
    print(f"\nJob Requirement: '{job_comp}'")
    
    # Find best match
    best_score = 0.0
    best_match = None
    
    all_user_terms = (profile.get('competencies', []) or []) + (profile.get('technical_skills', []) or [])
    
    for user_term in all_user_terms[:20]:  # Test first 20
        score = matcher.compute_similarity(job_comp, user_term)
        if score > best_score:
            best_score = score
            best_match = user_term
    
    print(f"  Best match: '{best_match}' (score: {best_score:.3f})")
    print(f"  Would match at 0.45 threshold: {'✓ YES' if best_score >= 0.45 else '✗ NO'}")
