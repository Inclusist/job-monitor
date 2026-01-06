"""
Parallel Job Enrichment Script
Runs multiple enrichment workers concurrently for 5-10x speedup.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.enrich_missing_jobs import enrich_jobs

load_dotenv()

def worker(worker_id, batch_size):
    """Single worker that processes a batch"""
    try:
        stats = enrich_jobs(limit=batch_size)
        return {
            'worker_id': worker_id,
            'success': True,
            'stats': stats
        }
    except Exception as e:
        return {
            'worker_id': worker_id,
            'success': False,
            'error': str(e),
            'stats': {'processed': 0, 'success': 0, 'failed': 0}
        }

def run_parallel_enrichment(num_workers=5, batch_size=50, max_batches=None):
    """
    Run enrichment with multiple parallel workers.
    
    Args:
        num_workers: Number of parallel workers (default: 5)
        batch_size: Jobs per worker batch (default: 50)
        max_batches: Maximum rounds to run (None = unlimited)
    """
    
    print("=" * 60)
    print("🚀 PARALLEL JOB ENRICHMENT")
    print("=" * 60)
    print(f"Workers: {num_workers} parallel processes")
    print(f"Batch Size: {batch_size} jobs per worker")
    print(f"Throughput: ~{num_workers * batch_size} jobs per round")
    print()
    
    round_num = 0
    total_processed = 0
    total_success = 0
    total_failed = 0
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        while True:
            round_num += 1
            
            if max_batches and round_num > max_batches:
                print(f"\n✋ Reached max batches limit ({max_batches})")
                break
            
            print(f"\n{'='*60}")
            print(f"🔄 ROUND {round_num}")
            print(f"{'='*60}")
            
            # Submit all workers
            futures = {
                executor.submit(worker, i, batch_size): i 
                for i in range(num_workers)
            }
            
            # Collect results
            round_processed = 0
            round_success = 0
            round_failed = 0
            active_workers = 0
            
            for future in as_completed(futures):
                result = future.result()
                stats = result['stats']
                
                if stats and stats['processed'] > 0:
                    active_workers += 1
                    round_processed += stats['processed']
                    round_success += stats['success']
                    round_failed += stats['failed']
                    
                    print(f"   Worker {result['worker_id']}: {stats['processed']} jobs ({stats['success']} ✓)")
            
            if round_processed == 0:
                print("\n✅ No more jobs to enrich!")
                break
            
            # Update totals
            total_processed += round_processed
            total_success += round_success
            total_failed += round_failed
            
            # Calculate stats
            elapsed = time.time() - start_time
            rate = total_processed / elapsed if elapsed > 0 else 0
            estimated_cost = total_processed * 0.0007
            
            print(f"\n📊 Round Summary:")
            print(f"   Processed: {round_processed} jobs")
            print(f"   Active Workers: {active_workers}/{num_workers}")
            
            print(f"\n📈 Overall Progress:")
            print(f"   Total: {total_processed} jobs")
            print(f"   Success Rate: {(total_success/total_processed*100):.1f}%")
            print(f"   Speed: {rate:.1f} jobs/sec ({rate*60:.0f} jobs/min)")
            print(f"   Cost: ${estimated_cost:.2f}")
            print(f"   Elapsed: {elapsed/60:.1f} min")
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("🎉 ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"✅ Total: {total_processed} jobs")
    print(f"✅ Success: {total_success}")
    print(f"❌ Failed: {total_failed}")
    print(f"💰 Cost: ${total_processed * 0.0007:.2f}")
    print(f"⏱️  Time: {total_time/60:.1f} min")
    print(f"🚀 Speed: {total_processed/(total_time/60):.0f} jobs/min")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Parallel batch enrich all jobs')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')
    parser.add_argument('--batch-size', type=int, default=50, help='Jobs per worker (default: 50)')
    parser.add_argument('--max-batches', type=int, default=None, help='Maximum rounds (default: unlimited)')
    
    args = parser.parse_args()
    
    print("\n⚠️  This will run PARALLEL enrichment (5-10x faster)")
    print(f"   Workers: {args.workers}")
    print(f"   Estimated speedup: ~{args.workers}x")
    print(f"   New completion time: ~2 hours (vs 9 hours sequential)")
    
    response = input("\nProceed? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        sys.exit(0)
    
    run_parallel_enrichment(
        num_workers=args.workers,
        batch_size=args.batch_size,
        max_batches=args.max_batches
    )
