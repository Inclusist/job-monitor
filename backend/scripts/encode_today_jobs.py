#!/usr/bin/env python3
"""
Encode job titles for jobs added today
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
from src.database.factory import get_database
from scripts.daily_job_cron import encode_new_jobs

load_dotenv()

if __name__ == "__main__":
    print('🔤 Encoding job titles for today\'s jobs...')
    print('   Model: TechWolf/JobBERT-v3 (1024-dim embeddings)')
    
    db = get_database()
    encoded_count = encode_new_jobs(db, limit=3000)
    
    if encoded_count > 0:
        print(f'✅ Successfully encoded {encoded_count} job titles')
    else:
        print('ℹ️  No jobs needed encoding')
    
    db.close()
