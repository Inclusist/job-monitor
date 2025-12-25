#!/usr/bin/env python3
"""Quick test to measure actual matching performance"""
import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, '/Users/prabhu.ramachandran/job-monitor')

from src.matching.matcher import run_background_matching

load_dotenv()

print("\n" + "="*80)
print(f"PERFORMANCE TEST: Full matching flow")
print("="*80 + "\n")

matching_status = {}

user_id = 4  # test@test.com - has valid CV about data/ML/AI
print(f"⏱️  Starting complete matching for user {user_id} (test@test.com)...")
print("This will process ALL unmatched jobs (2,090 expected)\n")

start = time.time()
run_background_matching(user_id, matching_status)
elapsed = time.time() - start

print("\n" + "="*80)
print(f"COMPLETE! Total time: {elapsed:.1f}s ({elapsed/60:.2f} minutes)")
print("="*80)
