#!/usr/bin/env python3
"""
Quick test script for Active Jobs DB 24h endpoint
Tests different parameter combinations to diagnose issues
"""

import os
import sys
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

API_KEY = os.getenv('ACTIVEJOBS_API_KEY')
BASE_URL = "https://active-jobs-db.p.rapidapi.com/active-ats-24h"

headers = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "active-jobs-db.p.rapidapi.com"
}

print("=" * 70)
print("ACTIVE JOBS DB 24H ENDPOINT - DEBUG TESTS")
print("=" * 70)

# Test 1: No filters (get ANY jobs from last 24h)
print("\n📋 TEST 1: No filters (any jobs from last 24h)")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} jobs")
else:
    print(f"❌ Response: {data}")

# Test 2: Location only (Berlin, Germany)
print("\n📋 TEST 2: Location = 'Berlin, Germany'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'location_filter': 'Berlin, Germany',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} jobs in Berlin, Germany")
else:
    print(f"❌ Response: {data}")

# Test 3: Location only (just Berlin)
print("\n📋 TEST 3: Location = 'Berlin' (without country)")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'location_filter': 'Berlin',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} jobs in Berlin")
else:
    print(f"❌ Response: {data}")

# Test 4: Location only (Germany)
print("\n📋 TEST 4: Location = 'Germany' (country only)")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'location_filter': 'Germany',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} jobs in Germany")
    if len(data) > 0:
        print(f"\nSample job titles:")
        for job in data[:3]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
            locations = job.get('locations_derived', [])
            print(f"    Location: {locations}")
else:
    print(f"❌ Response: {data}")

# Test 5: Simple title query (Machine Learning) + Germany
print("\n📋 TEST 5: Title = 'Machine&Learning' + Location = 'Germany'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'advanced_title_filter': 'Machine&Learning',
    'location_filter': 'Germany',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} Machine Learning jobs in Germany")
    if len(data) > 0:
        print(f"\nSample jobs:")
        for job in data[:3]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
else:
    print(f"❌ Response: {data}")

# Test 6a: Phrase query (old approach - word by word AND)
print("\n📋 TEST 6a: OLD - Title = 'Team&Lead&Machine&Learning' + Location = 'Berlin'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'advanced_title_filter': 'Team&Lead&Machine&Learning',
    'location_filter': 'Berlin',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} jobs")
    if len(data) > 0:
        print(f"\nSample jobs:")
        for job in data[:3]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
else:
    print(f"❌ Response: {data}")

# Test 6b: Phrase query (NEW approach - exact phrase)
print("\n📋 TEST 6b: NEW - Title = 'Team Lead Machine Learning' (exact phrase) + Location = 'Berlin'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'advanced_title_filter': "'Team Lead Machine Learning'",
    'location_filter': 'Berlin',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} jobs with exact phrase")
    if len(data) > 0:
        print(f"\nSample jobs:")
        for job in data[:3]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
else:
    print(f"❌ Response: {data}")

# Test 6c: Just Machine Learning phrase
print("\n📋 TEST 6c: Title = 'Machine Learning' (phrase) + Location = 'Berlin'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'advanced_title_filter': "'Machine Learning'",
    'location_filter': 'Berlin',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} Machine Learning jobs in Berlin")
    if len(data) > 0:
        print(f"\nSample jobs:")
        for job in data[:5]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
else:
    print(f"❌ Response: {data}")

print("\n" + "=" * 70)
print("🔄 NOW TESTING 7-DAY ENDPOINT (WEEK WINDOW)")
print("=" * 70)

BASE_URL_7D = "https://active-jobs-db.p.rapidapi.com/active-ats-7d"

# Test 7: 7-day endpoint - Germany only
print("\n📋 TEST 7: 7-DAY - Location = 'Germany'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'location_filter': 'Germany',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL_7D, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} jobs in Germany (7 days)")
    if len(data) > 0:
        print(f"\nSample job titles:")
        for job in data[:3]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
else:
    print(f"❌ Response: {data}")

# Test 8: 7-day - Machine Learning in Germany (exact phrase)
print("\n📋 TEST 8: 7-DAY - Title = 'Machine Learning' (phrase) + Location = 'Germany'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'advanced_title_filter': "'Machine Learning'",
    'location_filter': 'Germany',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL_7D, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} Machine Learning jobs in Germany (7 days)")
    if len(data) > 0:
        print(f"\nSample jobs:")
        for job in data[:3]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
            locations = job.get('locations_derived', [])
            print(f"    Location: {locations}")
else:
    print(f"❌ Response: {data}")

# Test 9: 7-day - Team Lead Machine Learning in Berlin (exact phrase)
print("\n📋 TEST 9: 7-DAY - Title = 'Team Lead Machine Learning' (phrase) + Location = 'Berlin'")
print("-" * 70)
params = {
    'limit': 10,
    'offset': 0,
    'advanced_title_filter': "'Team Lead Machine Learning'",
    'location_filter': 'Berlin',
    'include_ai': 'true'
}
print(f"Params: {params}")
response = requests.get(BASE_URL_7D, headers=headers, params=params)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
if isinstance(data, list):
    print(f"✅ Found {len(data)} Team Lead ML jobs in Berlin (7 days)")
    if len(data) > 0:
        print(f"\nJobs found:")
        for job in data[:5]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}")
            locations = job.get('locations_derived', [])
            print(f"    Location: {locations}")
else:
    print(f"❌ Response: {data}")

print("\n" + "=" * 70)
print("DIAGNOSIS:")
print("=" * 70)
print("24H TESTS:")
print("- If Test 1 returns jobs: API works, just need right filters")
print("- If Test 2/3 differs: Location format matters")
print("- If Test 4 returns jobs but Test 2/3 don't: Berlin might have no jobs today")
print("- If Test 5 returns jobs: Title query works, just not the specific combo")
print("- If Test 6 returns 0: No exact matches in last 24h (expected)")
print("\n7-DAY TESTS:")
print("- If Test 7 returns jobs: 7-day window has data")
print("- If Test 8 returns jobs: Machine Learning queries work over 7 days")
print("- If Test 9 returns jobs: Specific combo exists in 7-day window")
print("\n💡 RECOMMENDATION:")
print("If 7-day tests show jobs but 24h doesn't, consider using 'week' for daily cron")
print("This gives users more fresh jobs while still being recent.")
print("=" * 70)
