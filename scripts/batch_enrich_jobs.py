"""
Batch Job Enrichment Script
Enriches all unenriched jobs with AI-extracted competencies and metadata.
"""
import os
import sys
import time
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.enrich_missing_jobs import enrich_jobs

load_dotenv()

def run_batch_enrichment(batch_size=100, max_batches=None):
    """
    Run enrichment in batches until all jobs are processed.
    
    Args:
        batch_size: Number of jobs to process per batch
        max_batches: Maximum number of batches to run (None = unlimited)
    """
    
    print("=" * 60)
    print("🤖 BATCH JOB ENRICHMENT")
    print("=" * 60)
    print(f"Batch Size: {batch_size} jobs")
    print(f"Max Batches: {max_batches if max_batches else 'Unlimited'}")
    print()
    
    # Estimate costs
    # Claude Haiku: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens
    # Average job description: ~800 tokens input, ~400 tokens output
    # Cost per job: ~$0.0007
    
    estimated_cost_per_job = 0.0007
    
    batch_num = 0
    total_processed = 0
    total_success = 0
    total_failed = 0
    
    start_time = time.time()
    
    while True:
        batch_num += 1
        
        if max_batches and batch_num > max_batches:
            print(f"\n✋ Reached max batches limit ({max_batches})")
            break
        
        print(f"\n{'='*60}")
        print(f"📦 BATCH {batch_num}")
        print(f"{'='*60}")
        
        # Run enrichment
        stats = enrich_jobs(limit=batch_size)
        
        if stats is None or stats['processed'] == 0:
            print("\n✅ No more jobs to enrich!")
            break
        
        # Update totals
        batch_processed = stats['processed']
        batch_success = stats['success']
        batch_failed = stats['failed']
        
        total_processed += batch_processed
        total_success += batch_success
        total_failed += batch_failed
        
        # Calculate stats
        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        estimated_cost = total_processed * estimated_cost_per_job
        
        print(f"\n📊 Batch Stats:")
        print(f"   Processed: {batch_processed} | Success: {batch_success} | Failed: {batch_failed}")
        
        print(f"\n📈 Overall Progress:")
        print(f"   Total Processed: {total_processed}")
        print(f"   Success Rate: {(total_success/total_processed*100):.1f}%")
        print(f"   Processing Rate: {rate:.1f} jobs/sec")
        print(f"   Estimated Cost: ${estimated_cost:.2f}")
        print(f"   Time Elapsed: {elapsed/60:.1f} min")
        
        # Small delay between batches to avoid rate limits
        if batch_processed >= batch_size:
            print("\n⏸️  Pausing 2s between batches...")
            time.sleep(2)
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("🎉 ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"✅ Total Processed: {total_processed}")
    print(f"✅ Success: {total_success}")
    print(f"❌ Failed: {total_failed}")
    print(f"💰 Estimated Cost: ${total_processed * estimated_cost_per_job:.2f}")
    print(f"⏱️  Total Time: {total_time/60:.1f} minutes")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch enrich all jobs')
    parser.add_argument('--batch-size', type=int, default=100, help='Jobs per batch (default: 100)')
    parser.add_argument('--max-batches', type=int, default=None, help='Maximum batches to run (default: unlimited)')
    parser.add_argument('--dry-run', action='store_true', help='Show stats without processing')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE - No jobs will be processed")
        # Just show current status
        os.system("python scripts/check_enrichment_status.py")
    else:
        # Confirm with user
        print("\n⚠️  WARNING: This will process ALL unenriched jobs.")
        print("   Estimated cost: ~$4.50 for 6,353 jobs")
        print("   Estimated time: ~90 minutes")
        
        response = input("\nProceed? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            sys.exit(0)
        
        run_batch_enrichment(
            batch_size=args.batch_size,
            max_batches=args.max_batches
        )
