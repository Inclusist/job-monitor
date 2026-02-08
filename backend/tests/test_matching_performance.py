"""
Performance test for job matching pipeline
Measures time for each step to identify bottlenecks
"""
import pytest
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.matching.matcher import run_background_matching


@pytest.fixture
def db():
    """Database connection"""
    db_url = os.getenv('DATABASE_URL')
    db = PostgresDatabase(db_url)
    yield db
    db.close()


@pytest.fixture
def cv_manager(db):
    """CV Manager"""
    return PostgresCVManager(db.connection_pool)


@pytest.fixture
def test_user(cv_manager):
    """Get or create performance test user"""
    email = "perf_test@test.com"
    
    # Get or create user
    user = cv_manager.get_user_by_email(email)
    if not user:
        user_id = cv_manager.register_user(email, "test123", "Performance Test")
        user = cv_manager.get_user_by_id(user_id)
    
    return user


class TestMatchingPerformance:
    """Performance tests for job matching pipeline"""
    
    def test_01_measure_database_query_time(self, db, test_user):
        """Measure time to fetch unmatched jobs"""
        print(f"\n{'='*80}")
        print("TEST 1: Database Query Performance")
        print(f"{'='*80}")
        
        user_id = test_user['id']
        
        # Time the query
        start = time.time()
        unmatched_jobs = db.get_unfiltered_jobs_for_user(user_id)
        query_time = time.time() - start
        
        print(f"\n📊 Results:")
        print(f"  Unmatched jobs: {len(unmatched_jobs)}")
        print(f"  Query time: {query_time:.2f}s")
        if len(unmatched_jobs) > 0:
            print(f"  Time per job: {query_time/len(unmatched_jobs)*1000:.2f}ms")
        
        # Performance assertions
        if len(unmatched_jobs) > 0:
            time_per_job_ms = query_time / len(unmatched_jobs) * 1000
            print(f"\n⚠️  Performance Analysis:")
            if query_time > 5:
                print(f"  SLOW: Query took {query_time:.2f}s for {len(unmatched_jobs)} jobs")
                print(f"  Expected: <2s for 1000 jobs")
            if time_per_job_ms > 10:
                print(f"  SLOW: {time_per_job_ms:.2f}ms per job")
                print(f"  Expected: <5ms per job")
        
        return len(unmatched_jobs), query_time
    
    def test_02_measure_semantic_encoding_time(self, db, test_user):
        """Measure time for semantic analysis"""
        print(f"\n{'='*80}")
        print("TEST 2: Semantic Encoding Performance")
        print(f"{'='*80}")
        
        user_id = test_user['id']
        
        # Get sample of unmatched jobs
        unmatched_jobs = db.get_unfiltered_jobs_for_user(user_id)
        
        if len(unmatched_jobs) == 0:
            print("  ⚠️  No unmatched jobs to test")
            return
        
        # Test with first 100 jobs
        sample_size = min(100, len(unmatched_jobs))
        sample_jobs = unmatched_jobs[:sample_size]
        
        print(f"\n📊 Testing with {sample_size} jobs (of {len(unmatched_jobs)} total)")
        
        # Load sentence transformer
        from sentence_transformers import SentenceTransformer
        
        print("\n  Loading model...")
        start = time.time()
        model = SentenceTransformer('all-MiniLM-L6-v2')
        model_load_time = time.time() - start
        print(f"  Model loaded in {model_load_time:.2f}s")
        
        # Test single encoding with 100 jobs
        print("\n  Testing SINGLE job encoding (current method):")
        job_texts = [f"{j.get('title', '')} {j.get('company', '')} {j.get('description', '')[:200]}" for j in sample_jobs]
        
        start = time.time()
        for text in job_texts:
            embedding = model.encode(text, show_progress_bar=False)
        single_time = time.time() - start
        print(f"    {sample_size} jobs: {single_time:.2f}s ({single_time/sample_size*1000:.0f}ms per job)")
        
        # Test batch encoding with different batch sizes
        print("\n  Testing BATCH encoding (optimized method):")
        
        batch_sizes = [10, 50, 100]
        best_batch_size = 10
        best_time = float('inf')
        
        for batch_size in batch_sizes:
            start = time.time()
            for i in range(0, len(job_texts), batch_size):
                batch = job_texts[i:i+batch_size]
                embeddings = model.encode(batch, show_progress_bar=False)
            batch_time = time.time() - start
            
            print(f"    Batch size {batch_size:3d}: {batch_time:.2f}s ({batch_time/sample_size*1000:.0f}ms per job)")
            
            if batch_time < best_time:
                best_time = batch_time
                best_batch_size = batch_size
        
        speedup = single_time / best_time
        print(f"\n  ⚡ Best batch size: {best_batch_size}")
        print(f"  ⚡ Batch encoding is {speedup:.1f}x FASTER!")
        
        # Extrapolate to full dataset
        total_jobs = len(unmatched_jobs)
        estimated_single = (single_time / sample_size) * total_jobs
        estimated_batch = (best_time / sample_size) * total_jobs
        
        print(f"\n📈 Estimated time for {total_jobs} jobs:")
        print(f"  Single encoding: {estimated_single/60:.1f} minutes")
        print(f"  Batch encoding:  {estimated_batch/60:.1f} minutes")
        print(f"  Time saved:      {(estimated_single - estimated_batch)/60:.1f} minutes")
    
    def test_03_measure_complete_matching_flow(self, db, cv_manager, test_user):
        """Measure complete matching flow end-to-end"""
        print(f"\n{'='*80}")
        print("TEST 3: Complete Matching Flow (BASELINE)")
        print(f"{'='*80}")
        
        user_id = test_user['id']
        
        # Check if user has CV
        cv_data = cv_manager.get_user_cv(user_id)
        if not cv_data:
            print("\n  ⚠️  No CV for test user. Skipping full flow test.")
            print("  Upload a CV for the test user to run this test.")
            return
        
        # Get count of unmatched jobs
        unmatched_jobs = db.get_unfiltered_jobs_for_user(user_id)
        print(f"\n📊 Jobs to match: {len(unmatched_jobs)}")
        
        if len(unmatched_jobs) == 0:
            print("  ⚠️  No unmatched jobs. Skipping test.")
            return
        
        print(f"\n⏱️  Starting complete matching flow...")
        print(f"  This will take approximately {len(unmatched_jobs) * 0.1 / 60:.1f} minutes")
        print(f"  (User reported actual time: ~30 minutes)")
        
        # Run the actual matching
        start = time.time()
        run_background_matching(user_id)
        total_time = time.time() - start
        
        print(f"\n✅ Matching completed!")
        print(f"\n📊 Final Results:")
        print(f"  Total time: {total_time/60:.2f} minutes ({total_time:.1f} seconds)")
        print(f"  Jobs processed: {len(unmatched_jobs)}")
        print(f"  Time per job: {total_time/len(unmatched_jobs)*1000:.0f}ms")
        
        # Get match results
        matches = db.get_user_job_matches(user_id)
        print(f"  Total matches: {len(matches)}")
        
        # Performance analysis
        print(f"\n⚠️  Performance Analysis:")
        if total_time > 300:  # 5 minutes
            print(f"  CRITICAL: Matching took {total_time/60:.1f} minutes!")
            print(f"  Expected: <2 minutes for {len(unmatched_jobs)} jobs")
            print(f"  Slowdown: {total_time/120:.1f}x slower than target")
        elif total_time > 120:  # 2 minutes
            print(f"  WARNING: Matching took {total_time/60:.1f} minutes")
            print(f"  Target: <2 minutes")
        else:
            print(f"  GOOD: Matching completed in {total_time/60:.1f} minutes")
        
        return total_time, len(unmatched_jobs)


if __name__ == "__main__":
    print("Run with: pytest tests/test_matching_performance.py -v -s")
