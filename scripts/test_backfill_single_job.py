#!/usr/bin/env python3
"""
Test Backfill Flow - Single Job Test

Tests the complete backfill flow with minimal API usage:
- Creates test user
- Adds sample queries
- Fetches 1 job from JSearch
- Fetches 1 job from ActiveJobs
- Verifies backfill tracking works
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database
from src.database.postgres_cv_operations import PostgresCVManager
from src.collectors.jsearch import JSearchCollector
from src.collectors.activejobs import ActiveJobsCollector

load_dotenv()


def test_single_job_backfill():
    """Test backfill with just 1 job from each API"""
    print("=" * 70)
    print("BACKFILL TEST - Single Job from Each API")
    print("=" * 70)

    job_db = get_database()

    # Use CV manager for user operations
    if hasattr(job_db, 'connection_pool'):
        cv_manager = PostgresCVManager(job_db.connection_pool)
    else:
        print("❌ Error: PostgreSQL connection pool not available")
        return

    db = cv_manager  # Use cv_manager for all operations

    try:
        # ========================================
        # Step 1: Create test user
        # ========================================
        print("\n1️⃣  Creating test user...")

        test_email = "test.backfill@example.com"
        user = db.get_user(test_email)

        if user:
            user_id = user['id']
            print(f"   ✓ Test user exists (ID: {user_id})")
        else:
            user_id = db.create_user(
                email=test_email,
                password_hash="test_hash_backfill"
            )
            print(f"   ✓ Created test user (ID: {user_id})")

        # ========================================
        # Step 2: Add sample query
        # ========================================
        print("\n2️⃣  Adding sample search query...")

        title = "Data Scientist"
        location = "Berlin"

        row_count = db.add_user_search_queries(
            user_id=user_id,
            query_name="Test Search",
            title_keywords=[title],
            locations=[location],
            ai_work_arrangement="Remote OK",
            ai_seniority="Senior",
            priority=10
        )
        print(f"   ✓ Added query: '{title}' in '{location}'")

        # ========================================
        # Step 3: Check if already backfilled
        # ========================================
        print("\n3️⃣  Checking backfill status...")

        unbacked = db.get_unbacked_combinations_for_user(user_id)

        if not unbacked:
            print(f"   ℹ️  Combination already backfilled by another user")
            print(f"   This is GOOD - shows deduplication is working!")

            # Check what's in tracking table
            is_backfilled = db.is_combination_backfilled(
                title_keyword=title,
                location=location,
                ai_work_arrangement="Remote OK",
                ai_seniority="Senior"
            )
            print(f"   ✓ Verified: Combination exists in backfill_tracking: {is_backfilled}")

        else:
            print(f"   ✓ Combination needs backfill: {len(unbacked)} combination(s)")

        # ========================================
        # Step 4: Fetch 1 job from JSearch
        # ========================================
        print("\n4️⃣  Testing JSearch API (fetching 1 job)...")

        jsearch_key = os.getenv('JSEARCH_API_KEY')
        if not jsearch_key:
            print("   ⚠️  JSEARCH_API_KEY not set, skipping JSearch test")
            jsearch_job = None
        else:
            try:
                jsearch = JSearchCollector(jsearch_key)
                jobs = jsearch.search_jobs(
                    query=title,
                    num_pages=1,
                    page_size=1,  # Just 1 job!
                    date_posted="month",
                    country="de"
                )

                if jobs:
                    jsearch_job = jobs[0]
                    print(f"   ✓ Fetched 1 job from JSearch:")
                    print(f"      Title: {jsearch_job.get('title', 'N/A')}")
                    print(f"      Company: {jsearch_job.get('company', 'N/A')}")
                    print(f"      Location: {jsearch_job.get('location', 'N/A')}")
                else:
                    print(f"   ⚠️  No jobs found on JSearch")
                    jsearch_job = None

            except Exception as e:
                print(f"   ❌ JSearch error: {e}")
                jsearch_job = None

        # ========================================
        # Step 5: Fetch 1 job from ActiveJobs
        # ========================================
        print("\n5️⃣  Testing ActiveJobs API (fetching 1 job)...")

        activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')
        if not activejobs_key:
            print("   ⚠️  ACTIVEJOBS_API_KEY not set, skipping ActiveJobs test")
            activejobs_job = None
        else:
            try:
                activejobs = ActiveJobsCollector(activejobs_key)
                jobs = activejobs.search_jobs(
                    query=title,
                    location=location,
                    num_pages=1,
                    results_per_page=1,  # Just 1 job!
                    date_posted="week",
                    ai_work_arrangement="Remote OK",
                    ai_seniority="Senior"
                )

                if jobs:
                    activejobs_job = jobs[0]
                    print(f"   ✓ Fetched 1 job from ActiveJobs:")
                    print(f"      Title: {activejobs_job.get('title', 'N/A')}")
                    print(f"      Company: {activejobs_job.get('company', 'N/A')}")
                    print(f"      Location: {activejobs_job.get('location', 'N/A')}")
                else:
                    print(f"   ⚠️  No jobs found on ActiveJobs")
                    activejobs_job = None

            except Exception as e:
                print(f"   ❌ ActiveJobs error: {e}")
                activejobs_job = None

        # ========================================
        # Step 6: Store jobs in database
        # ========================================
        print("\n6️⃣  Storing jobs in database...")

        stored_count = 0

        for job, source in [(jsearch_job, 'JSearch'), (activejobs_job, 'ActiveJobs')]:
            if job:
                try:
                    job_id = job.get('external_id') or job.get('job_id') or f"{job['company']}_{job['title']}"
                    job['job_id'] = job_id

                    result = db.add_job(job)
                    if result:
                        stored_count += 1
                        print(f"   ✓ Stored job from {source}")
                    else:
                        print(f"   ℹ️  Job from {source} already exists (duplicate)")

                except Exception as e:
                    print(f"   ⚠️  Could not store job from {source}: {e}")

        print(f"\n   Total jobs stored: {stored_count}")

        # ========================================
        # Step 7: Mark as backfilled
        # ========================================
        print("\n7️⃣  Marking combination as backfilled...")

        if unbacked:  # Only mark if it wasn't already backfilled
            result = db.mark_combination_backfilled(
                title_keyword=title,
                location=location,
                ai_work_arrangement="Remote OK",
                ai_seniority="Senior",
                jobs_found=stored_count
            )

            if result:
                print(f"   ✓ Marked as backfilled in tracking table")
            else:
                print(f"   ℹ️  Already in tracking table")
        else:
            print(f"   ℹ️  Skipped (already backfilled)")

        # ========================================
        # Step 8: Verify backfill tracking
        # ========================================
        print("\n8️⃣  Verifying backfill tracking...")

        is_backfilled = db.is_combination_backfilled(
            title_keyword=title,
            location=location,
            ai_work_arrangement="Remote OK",
            ai_seniority="Senior"
        )

        print(f"   ✓ Combination in backfill_tracking: {is_backfilled}")

        # ========================================
        # Step 9: Test deduplication
        # ========================================
        print("\n9️⃣  Testing deduplication (create second user)...")

        test_email2 = "test.backfill2@example.com"
        user2 = db.get_user(test_email2)

        if user2:
            user2_id = user2['id']
        else:
            user2_id = db.create_user(
                email=test_email2,
                password_hash="test_hash_backfill2"
            )

        # Add same query for second user
        db.add_user_search_queries(
            user_id=user2_id,
            query_name="Test Search",
            title_keywords=[title],
            locations=[location],
            ai_work_arrangement="Remote OK",
            ai_seniority="Senior",
            priority=10
        )

        # Check if it needs backfill
        unbacked2 = db.get_unbacked_combinations_for_user(user2_id)

        if unbacked2:
            print(f"   ❌ FAIL: User 2 should not need backfill!")
            print(f"   Deduplication not working")
        else:
            print(f"   ✅ SUCCESS: User 2 doesn't need backfill!")
            print(f"   Deduplication working correctly!")

        # ========================================
        # Summary
        # ========================================
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        print(f"\n✅ Test completed!")
        print(f"\nResults:")
        print(f"   • User 1 created: ✓")
        print(f"   • Query added: '{title}' in '{location}'")
        print(f"   • JSearch job fetched: {'✓' if jsearch_job else '✗'}")
        print(f"   • ActiveJobs job fetched: {'✓' if activejobs_job else '✗'}")
        print(f"   • Jobs stored in DB: {stored_count}")
        print(f"   • Marked as backfilled: ✓")
        print(f"   • Deduplication works: {'✓' if not unbacked2 else '✗'}")

        print(f"\n💡 API Quota Used:")
        print(f"   • JSearch: {1 if jsearch_job else 0} job")
        print(f"   • ActiveJobs: {1 if activejobs_job else 0} job")
        print(f"   • Total: {(1 if jsearch_job else 0) + (1 if activejobs_job else 0)} jobs")

        print(f"\n✨ Next steps:")
        print(f"   1. Upload a CV in production")
        print(f"   2. Watch the backfill automatically run")
        print(f"   3. Jobs will be ready immediately!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if hasattr(job_db, 'close'):
            job_db.close()


if __name__ == "__main__":
    test_single_job_backfill()
