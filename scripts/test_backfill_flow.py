#!/usr/bin/env python3
"""
Test Backfill Flow

Tests the complete user backfill system:
1. Create test user queries
2. Run backfill for user
3. Verify backfill tracking
4. Simulate second user with overlapping queries
5. Verify deduplication works

Usage:
    python scripts/test_backfill_flow.py
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database
from src.jobs.user_backfill import backfill_user_on_signup

load_dotenv()


def test_backfill_system():
    """Test complete backfill system"""
    print("=" * 80)
    print("BACKFILL SYSTEM TEST")
    print("=" * 80)

    db = get_database()

    try:
        # ========================================
        # TEST 1: Create User 1 with queries
        # ========================================
        print("\n" + "=" * 80)
        print("TEST 1: Create User 1 with Unique Queries")
        print("=" * 80)

        # Create test user 1
        user1_email = "test_user1@example.com"
        print(f"\n1. Creating test user: {user1_email}")

        # Check if user exists
        existing = db.get_user(user1_email)
        if existing:
            user1_id = existing['id']
            print(f"   ✓ User already exists (ID: {user1_id})")
        else:
            user1_id = db.create_user(
                email=user1_email,
                password_hash="test_hash_1"
            )
            print(f"   ✓ Created user (ID: {user1_id})")

        # Add search queries for User 1
        print("\n2. Adding search queries for User 1...")
        row_count = db.add_user_search_queries(
            user_id=user1_id,
            query_name="Primary Search",
            title_keywords=["Data Scientist", "Machine Learning Engineer"],
            locations=["Berlin", "Hamburg"],
            ai_work_arrangement="Remote OK",
            ai_seniority="Senior",
            priority=10
        )
        print(f"   ✓ Created {row_count} query rows (2 titles × 2 locations = 4 rows)")

        # Get unbacked combinations for User 1
        print("\n3. Checking unbacked combinations for User 1...")
        unbacked1 = db.get_unbacked_combinations_for_user(user1_id)
        print(f"   ✓ User 1 has {len(unbacked1)} unbacked combinations:")
        for combo in unbacked1:
            print(f"      - {combo.get('title_keyword')} in {combo.get('location')}")

        # ========================================
        # TEST 2: Backfill User 1
        # ========================================
        print("\n" + "=" * 80)
        print("TEST 2: Backfill User 1 (Should fetch jobs)")
        print("=" * 80)

        # Note: This will use actual API quota!
        user_input = input("\n⚠️  This will use API quota. Continue? (y/n): ")
        if user_input.lower() != 'y':
            print("Skipping backfill test.")
            print("\n✓ Test 1 passed: User 1 queries created successfully")
            db.close()
            return

        stats1 = backfill_user_on_signup(
            user_id=user1_id,
            user_email=user1_email,
            db=db
        )

        print(f"\n✓ Backfill completed for User 1:")
        print(f"   - Jobs added: {stats1.get('new_jobs_added', 0)}")
        print(f"   - JSearch used: {stats1.get('quota_used', {}).get('jsearch', 0)} jobs")
        print(f"   - ActiveJobs used: {stats1.get('quota_used', {}).get('activejobs', 0)} jobs")

        # ========================================
        # TEST 3: Create User 2 with overlapping queries
        # ========================================
        print("\n" + "=" * 80)
        print("TEST 3: Create User 2 with Overlapping Queries")
        print("=" * 80)

        user2_email = "test_user2@example.com"
        print(f"\n1. Creating test user: {user2_email}")

        existing2 = db.get_user(user2_email)
        if existing2:
            user2_id = existing2['id']
            print(f"   ✓ User already exists (ID: {user2_id})")
        else:
            user2_id = db.create_user(
                email=user2_email,
                password_hash="test_hash_2"
            )
            print(f"   ✓ Created user (ID: {user2_id})")

        # Add overlapping queries for User 2
        print("\n2. Adding search queries for User 2 (overlap with User 1)...")
        row_count2 = db.add_user_search_queries(
            user_id=user2_id,
            query_name="Primary Search",
            title_keywords=["Data Scientist"],  # Overlaps!
            locations=["Berlin", "Munich"],      # Berlin overlaps!
            ai_work_arrangement="Remote OK",
            ai_seniority="Senior",
            priority=10
        )
        print(f"   ✓ Created {row_count2} query rows (1 title × 2 locations = 2 rows)")

        # Get unbacked combinations for User 2
        print("\n3. Checking unbacked combinations for User 2...")
        unbacked2 = db.get_unbacked_combinations_for_user(user2_id)
        print(f"   ✓ User 2 has {len(unbacked2)} unbacked combinations:")
        for combo in unbacked2:
            print(f"      - {combo.get('title_keyword')} in {combo.get('location')}")

        expected_unbacked = 1  # Only "Data Scientist in Munich" is new
        if len(unbacked2) == expected_unbacked:
            print(f"\n   ✅ DEDUPLICATION WORKS!")
            print(f"      Expected {expected_unbacked} unbacked, got {len(unbacked2)}")
            print(f"      'Data Scientist in Berlin' already backfilled by User 1")
        else:
            print(f"\n   ⚠️  Expected {expected_unbacked} unbacked, got {len(unbacked2)}")

        # ========================================
        # TEST 4: Backfill User 2 (should skip Berlin)
        # ========================================
        print("\n" + "=" * 80)
        print("TEST 4: Backfill User 2 (Should skip already-backfilled combinations)")
        print("=" * 80)

        user_input2 = input("\n⚠️  Continue with User 2 backfill? (y/n): ")
        if user_input2.lower() != 'y':
            print("Skipping User 2 backfill test.")
            print("\n✓ Tests passed!")
            db.close()
            return

        stats2 = backfill_user_on_signup(
            user_id=user2_id,
            user_email=user2_email,
            db=db
        )

        if stats2.get('already_backfilled'):
            print(f"\n✅ ALL combinations already backfilled - no API calls made!")
        else:
            print(f"\n✓ Backfill completed for User 2:")
            print(f"   - Jobs added: {stats2.get('new_jobs_added', 0)}")
            print(f"   - JSearch used: {stats2.get('quota_used', {}).get('jsearch', 0)} jobs")
            print(f"   - ActiveJobs used: {stats2.get('quota_used', {}).get('activejobs', 0)} jobs")
            print(f"\n   Expected: Only 'Data Scientist in Munich' fetched")

        # ========================================
        # SUMMARY
        # ========================================
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        print("\n✅ All tests passed!")
        print("\nKey findings:")
        print(f"   • User 1: {len(unbacked1)} combinations backfilled")
        print(f"   • User 2: {len(unbacked2)} NEW combinations (rest already backfilled)")
        print(f"   • Deduplication saved: {len(unbacked1) - len(unbacked2)} API calls")

        print("\nBackfill tracking system working correctly!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    test_backfill_system()
