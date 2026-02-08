#!/usr/bin/env python3
"""
Example: Managing User Search Queries

Demonstrates how to create, update, and manage personalized search queries
for users using the pipe operator (|) for OR logic.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database

load_dotenv()


def example_create_queries():
    """Example: Creating search queries for users"""
    print("=" * 60)
    print("Example 1: Creating User Search Queries")
    print("=" * 60)

    db = get_database()

    # Example 1: Data scientist looking in Berlin and Hamburg
    print("\n1. Creating query for data scientist...")
    query_id = db.add_user_search_query(
        user_id=1,
        query_name="Primary Search",
        title_keywords="data scientist|ML engineer|AI researcher",  # OR logic
        locations="Berlin|Hamburg",                                 # OR logic
        ai_work_arrangement="Remote OK|Hybrid",                     # OR logic
        ai_seniority="Senior|Lead",
        priority=10,
        max_results=100
    )

    if query_id:
        print(f"   ✓ Created query ID: {query_id}")
        print(f"   This will search:")
        print(f"     - Titles: 'data scientist' OR 'ML engineer' OR 'AI researcher'")
        print(f"     - Locations: Berlin OR Hamburg")
        print(f"     - Work: Remote OK OR Hybrid")
        print(f"     - Seniority: Senior OR Lead")

    # Example 2: Software engineer looking for remote work
    print("\n2. Creating remote software engineer query...")
    query_id = db.add_user_search_query(
        user_id=1,
        query_name="Remote Only",
        title_keywords="senior software engineer|lead developer",
        locations=None,  # Anywhere
        ai_work_arrangement="Remote Solely",
        priority=8,
        max_results=50
    )

    if query_id:
        print(f"   ✓ Created query ID: {query_id}")
        print(f"   This searches for remote-only positions anywhere")

    # Example 3: Product manager in Munich
    print("\n3. Creating product manager query...")
    query_id = db.add_user_search_query(
        user_id=1,
        query_name="Product Management",
        title_keywords="product manager|product owner|head of product",
        locations="Munich|Frankfurt",
        ai_seniority="Mid|Senior",
        ai_industry="Technology",
        priority=5,
        max_results=30
    )

    if query_id:
        print(f"   ✓ Created query ID: {query_id}")


def example_view_queries():
    """Example: Viewing user queries"""
    print("\n" + "=" * 60)
    print("Example 2: Viewing User Queries")
    print("=" * 60)

    db = get_database()

    queries = db.get_user_search_queries(user_id=1, active_only=True)

    print(f"\nFound {len(queries)} active queries for user 1:")

    for i, query in enumerate(queries, 1):
        print(f"\n  Query {i}: {query['query_name']} (Priority: {query['priority']})")
        print(f"    Title keywords: {query['title_keywords'] or 'Any'}")
        print(f"    Locations: {query['locations'] or 'Any'}")
        print(f"    Work arrangement: {query['ai_work_arrangement'] or 'Any'}")
        print(f"    Seniority: {query['ai_seniority'] or 'Any'}")
        print(f"    Max results: {query['max_results']}")
        print(f"    Created: {query['created_date']}")

        if query['last_run_date']:
            print(f"    Last run: {query['last_run_date']}")
            print(f"    Last job count: {query['last_job_count']}")


def example_update_queries():
    """Example: Updating queries"""
    print("\n" + "=" * 60)
    print("Example 3: Updating Queries")
    print("=" * 60)

    db = get_database()

    queries = db.get_user_search_queries(user_id=1, active_only=True)

    if queries:
        query_id = queries[0]['id']

        # Update locations
        print(f"\n1. Updating locations for query {query_id}...")
        success = db.update_user_search_query(
            query_id=query_id,
            locations="Berlin|Hamburg|Cologne"  # Added Cologne
        )

        if success:
            print(f"   ✓ Updated locations")

        # Update priority
        print(f"\n2. Changing priority...")
        success = db.update_user_search_query(
            query_id=query_id,
            priority=15  # Higher priority
        )

        if success:
            print(f"   ✓ Priority updated to 15")

        # Temporarily disable query
        print(f"\n3. Temporarily disabling query...")
        success = db.update_user_search_query(
            query_id=query_id,
            is_active=False
        )

        if success:
            print(f"   ✓ Query disabled (won't run until re-enabled)")


def example_complex_queries():
    """Example: Complex multi-query strategies"""
    print("\n" + "=" * 60)
    print("Example 4: Complex Multi-Query Strategies")
    print("=" * 60)

    db = get_database()

    # Strategy: Cast a wide net with multiple complementary queries

    print("\n1. Local leadership roles...")
    db.add_user_search_query(
        user_id=1,
        query_name="Local Leadership",
        title_keywords="head of data|VP engineering|CTO|director of AI",
        locations="Berlin",
        ai_seniority="Lead|Executive",
        priority=10,
        max_results=20
    )

    print("\n2. Remote senior positions...")
    db.add_user_search_query(
        user_id=1,
        query_name="Remote Senior",
        title_keywords="senior data scientist|staff engineer",
        ai_work_arrangement="Remote Solely",
        ai_seniority="Senior|Staff",
        priority=8,
        max_results=50
    )

    print("\n3. Startup opportunities...")
    db.add_user_search_query(
        user_id=1,
        query_name="Startup Scene",
        title_keywords="founding engineer|early stage|technical co-founder",
        locations="Berlin|Munich",
        ai_employment_type="Full-time",
        priority=5,
        max_results=15
    )

    print("\n4. Consulting gigs...")
    db.add_user_search_query(
        user_id=1,
        query_name="Consulting",
        title_keywords="ML consultant|data science consultant",
        ai_employment_type="Contract",
        priority=3,
        max_results=10
    )

    print("\n   ✓ Created 4 complementary queries")
    print("\n   Strategy:")
    print("     - High priority: Local leadership (immediate interest)")
    print("     - Medium priority: Remote senior roles (good fallback)")
    print("     - Lower priority: Startups and consulting (exploratory)")


def example_industry_specific():
    """Example: Industry-specific queries"""
    print("\n" + "=" * 60)
    print("Example 5: Industry-Specific Queries")
    print("=" * 60)

    db = get_database()

    # Different queries for different industries

    print("\n1. Automotive industry...")
    db.add_user_search_query(
        user_id=1,
        query_name="Automotive AI",
        title_keywords="ML engineer|data scientist",
        locations="Wolfsburg|Munich|Stuttgart",
        ai_industry="Automotive",
        ai_seniority="Mid|Senior",
        priority=10,
        max_results=50
    )

    print("\n2. Finance sector...")
    db.add_user_search_query(
        user_id=1,
        query_name="FinTech",
        title_keywords="quantitative researcher|ML engineer|data scientist",
        locations="Frankfurt|Berlin",
        ai_industry="Finance|FinTech",
        ai_seniority="Senior|Lead",
        priority=8,
        max_results=30
    )

    print("\n3. E-commerce/retail...")
    db.add_user_search_query(
        user_id=1,
        query_name="E-Commerce",
        title_keywords="data scientist|ML engineer|personalization engineer",
        locations="Berlin|Hamburg",
        ai_industry="E-Commerce|Retail",
        priority=6,
        max_results=40
    )

    print("\n   ✓ Created industry-specific queries")
    print("\n   This targets:")
    print("     - Automotive hubs (Wolfsburg, Munich, Stuttgart)")
    print("     - Finance center (Frankfurt)")
    print("     - E-commerce/tech hubs (Berlin, Hamburg)")


def main():
    """Run all examples"""
    try:
        example_create_queries()
        example_view_queries()
        example_update_queries()
        example_complex_queries()
        example_industry_specific()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

        print("\n💡 Next steps:")
        print("   1. Run: python scripts/user_query_loader.py")
        print("   2. Jobs will be fetched based on these queries")
        print("   3. Check quota usage and adjust max_results if needed")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
