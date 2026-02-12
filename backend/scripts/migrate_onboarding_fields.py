#!/usr/bin/env python3
"""
Migration: Add onboarding fields to users table
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.factory import get_database

load_dotenv()

def migrate_onboarding_fields():
    """Add onboarding tracking fields to users table"""
    db = get_database()
    conn = db._get_connection()
    cursor = conn.cursor()
    
    try:
        print("Starting migration: Add onboarding fields...")
        
        # Add onboarding_completed field
        print("  - Adding onboarding_completed field...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false
        """)
        
        # Add onboarding_step field
        print("  - Adding onboarding_step field...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS onboarding_step INTEGER DEFAULT 0
        """)
        
        # Add onboarding_skipped field
        print("  - Adding onboarding_skipped field...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS onboarding_skipped BOOLEAN DEFAULT false
        """)
        
        # Mark existing users as completed (grandfather clause)
        print("  - Marking existing users as onboarding completed...")
        cursor.execute("""
            UPDATE users 
            SET onboarding_completed = true 
            WHERE created_date < NOW()
        """)
        
        affected_rows = cursor.rowcount
        print(f"  - Marked {affected_rows} existing users as completed")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
        
    finally:
        cursor.close()
        db._return_connection(conn)

if __name__ == '__main__':
    migrate_onboarding_fields()
