"""
Test Pre-filtering by Location and Work Arrangement

Tests that jobs are correctly filtered based on:
- User's location preferences
- User's work arrangement preferences (remote, hybrid, on-site)
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

def location_matches(user_locs, job_loc_str, job_loc_array):
    """Check if job location matches any user location (same logic as matcher.py)"""
    if not user_locs:
        return True  # No filter
    for user_loc in user_locs:
        if not user_loc:
            continue
        user_loc_lower = user_loc.lower()
        # Check string field
        if user_loc_lower in job_loc_str.lower():
            return True
        # Check array field
        for loc in job_loc_array:
            if loc and user_loc_lower in loc.lower():
                return True
    return False

def test_prefiltering(user_location, preferred_locs, work_pref):
    """Test pre-filtering with given user preferences"""
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get recent jobs
    cur.execute("""
        SELECT 
            id,
            title,
            location,
            locations_derived,
            ai_work_arrangement
        FROM jobs
        WHERE created_at > NOW() - INTERVAL '24 hours'
        LIMIT 1000
    """)
    
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"Testing Pre-filtering")
    print(f"{'='*80}")
    print(f"User Location: {user_location}")
    print(f"Preferred Locations: {preferred_locs}")
    print(f"Work Preference: {work_pref}")
    print(f"Total Jobs: {len(jobs)}")
    print(f"{'='*80}\n")
    
    # Apply pre-filtering logic (copied from matcher.py)
    filtered_jobs = []
    stats = {
        'remote': 0,
        'hybrid': 0,
        'on-site': 0,
        'unspecified': 0,
        'rejected': 0
    }
    
    for job in jobs:
        job_work = (job.get('ai_work_arrangement') or '').lower()
        job_location = job.get('location') or ''
        job_locations = job.get('locations_derived') or []
        
        include = False
        reason = ""
        
        if job_work == 'remote' or job_work == 'remote ok':
            if work_pref in ['remote', 'flexible', 'remote_preferred']:
                include = True
                reason = "Remote + user accepts remote"
                stats['remote'] += 1
        elif job_work == 'hybrid':
            if work_pref in ['hybrid', 'flexible', 'hybrid_preferred']:
                if location_matches(preferred_locs or [user_location], job_location, job_locations):
                    include = True
                    reason = "Hybrid + location match"
                    stats['hybrid'] += 1
        elif job_work in ['on-site', 'onsite']:
            # On-site: flexible users check preferred_locs, on-site users check user_location only
            if work_pref == 'flexible':
                if location_matches(preferred_locs or [user_location], job_location, job_locations):
                    include = True
                    reason = "On-site + location match (flexible)"
                    stats['on-site'] += 1
            else:
                if location_matches([user_location] if user_location else [], job_location, job_locations):
                    include = True
                    reason = "On-site + user location match"
                    stats['on-site'] += 1
        else:
            if location_matches(preferred_locs, job_location, job_locations):
                include = True
                reason = "No work pref + location match"
                stats['unspecified'] += 1
        
        if include:
            filtered_jobs.append({
                'job': job,
                'reason': reason
            })
        else:
            stats['rejected'] += 1
    
    # Print results
    print(f"Results:")
    print(f"  ✅ Passed filter: {len(filtered_jobs)} ({len(filtered_jobs)*100//len(jobs) if jobs else 0}%)")
    print(f"  ❌ Rejected: {stats['rejected']} ({stats['rejected']*100//len(jobs) if jobs else 0}%)")
    print(f"\nBreakdown by Work Arrangement:")
    print(f"  Remote jobs: {stats['remote']}")
    print(f"  Hybrid jobs: {stats['hybrid']}")
    print(f"  On-site jobs: {stats['on-site']}")
    print(f"  Unspecified work: {stats['unspecified']}")
    
    # Show sample matches
    print(f"\nSample Matches (first 8):")
    print(f"{'-'*80}")
    for i, match in enumerate(filtered_jobs[:8], 1):
        job = match['job']
        print(f"{i}. {job['title'][:50]}")
        print(f"   Location: {(job['location'] or '')[:60]}")
        print(f"   Work: {job['ai_work_arrangement']}")
        print(f"   Reason: {match['reason']}")
    
    return len(filtered_jobs), len(jobs)

if __name__ == "__main__":
    print("\n🧪 SCENARIO 1: User in Hamburg, wants Remote/Hybrid jobs")
    passed, total = test_prefiltering(
        user_location="Hamburg",
        preferred_locs=["Hamburg", "Germany"],
        work_pref="remote_preferred"
    )
    
    print("\n\n🧪 SCENARIO 2: User in Berlin, only On-site in Berlin")
    passed, total = test_prefiltering(
        user_location="Berlin",
        preferred_locs=["Berlin"],
        work_pref="onsite"
    )
    
    print("\n\n🧪 SCENARIO 3: User flexible, any location in Germany")
    passed, total = test_prefiltering(
        user_location="Munich",
        preferred_locs=["Germany"],
        work_pref="flexible"
    )
    
    print("\n\n✅ Pre-filtering test complete!")
