"""
Migrate users, CVs, and CV profiles from SQLite to PostgreSQL

Usage:
    python scripts/migrate_users_to_postgres.py <postgresql_url>
    
Example:
    python scripts/migrate_users_to_postgres.py "postgresql://user:pass@host:5432/dbname"
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.cv_operations import CVManager
from src.database.postgres_operations import PostgresDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_users(sqlite_db: CVManager, postgres_db: PostgresDatabase) -> tuple:
    """
    Migrate users from SQLite to PostgreSQL
    
    Returns:
        tuple: (migrated_count, skipped_count, error_count)
    """
    logger.info("Starting users migration...")
    
    # Get all users from SQLite
    conn = sqlite_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    
    users = []
    for row in cursor.fetchall():
        users.append(dict(row))
    
    conn.close()
    
    logger.info(f"Found {len(users)} users to migrate")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for user in users:
        try:
            pg_conn = postgres_db._get_connection()
            pg_cursor = pg_conn.cursor()
            
            # Check if user already exists
            pg_cursor.execute("SELECT id FROM users WHERE email = %s", (user['email'],))
            if pg_cursor.fetchone():
                skipped += 1
                pg_cursor.close()
                postgres_db._return_connection(pg_conn)
                continue
            
            # Insert user
            pg_cursor.execute("""
                INSERT INTO users (
                    email, password_hash, name, user_role, location,
                    created_date, last_updated, is_active, preferences,
                    last_filter_run, preferences_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user['email'],
                user['password_hash'],
                user['name'],
                user.get('current_role'),  # Map current_role to user_role
                user.get('location'),
                user['created_date'],
                user['last_updated'],
                user.get('is_active', 1),
                user.get('preferences'),
                user.get('last_filter_run'),
                user.get('preferences_updated')
            ))
            
            pg_conn.commit()
            migrated += 1
            
            if migrated % 10 == 0:
                logger.info(f"Migrated {migrated} users...")
                
            pg_cursor.close()
            postgres_db._return_connection(pg_conn)
            
        except Exception as e:
            errors += 1
            logger.error(f"Error migrating user {user['email']}: {e}")
            if 'pg_conn' in locals():
                pg_conn.rollback()
                pg_cursor.close()
                postgres_db._return_connection(pg_conn)
    
    logger.info(f"Users migration complete: {migrated} migrated, {skipped} skipped, {errors} errors")
    return (migrated, skipped, errors)


def migrate_cvs(sqlite_db: CVManager, postgres_db: PostgresDatabase) -> tuple:
    """
    Migrate CVs from SQLite to PostgreSQL
    
    Returns:
        tuple: (migrated_count, skipped_count, error_count)
    """
    logger.info("Starting CVs migration...")
    
    # Get all CVs from SQLite
    conn = sqlite_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cvs")
    
    cvs = []
    for row in cursor.fetchall():
        cvs.append(dict(row))
    
    conn.close()
    
    logger.info(f"Found {len(cvs)} CVs to migrate")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for cv in cvs:
        try:
            pg_conn = postgres_db._get_connection()
            pg_cursor = pg_conn.cursor()
            
            # Check if CV already exists
            pg_cursor.execute(
                "SELECT id FROM cvs WHERE user_id = %s AND file_hash = %s", 
                (cv['user_id'], cv.get('file_hash'))
            )
            if pg_cursor.fetchone():
                skipped += 1
                pg_cursor.close()
                postgres_db._return_connection(pg_conn)
                continue
            
            # Insert CV
            pg_cursor.execute("""
                INSERT INTO cvs (
                    user_id, file_name, file_path, file_type, file_size,
                    file_hash, uploaded_date, is_primary, version, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                cv['user_id'],
                cv['file_name'],
                cv['file_path'],
                cv['file_type'],
                cv.get('file_size'),
                cv.get('file_hash'),
                cv['uploaded_date'],
                cv.get('is_primary', 0),
                cv.get('version', 1),
                cv.get('status', 'active')
            ))
            
            pg_conn.commit()
            migrated += 1
            
            if migrated % 10 == 0:
                logger.info(f"Migrated {migrated} CVs...")
                
            pg_cursor.close()
            postgres_db._return_connection(pg_conn)
            
        except Exception as e:
            errors += 1
            logger.error(f"Error migrating CV {cv['id']}: {e}")
            if 'pg_conn' in locals():
                pg_conn.rollback()
                pg_cursor.close()
                postgres_db._return_connection(pg_conn)
    
    logger.info(f"CVs migration complete: {migrated} migrated, {skipped} skipped, {errors} errors")
    return (migrated, skipped, errors)


def migrate_cv_profiles(sqlite_db: CVManager, postgres_db: PostgresDatabase) -> tuple:
    """
    Migrate CV profiles from SQLite to PostgreSQL
    
    Returns:
        tuple: (migrated_count, skipped_count, error_count)
    """
    logger.info("Starting CV profiles migration...")
    
    # Get all CV profiles from SQLite
    conn = sqlite_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cv_profiles")
    
    profiles = []
    for row in cursor.fetchall():
        profiles.append(dict(row))
    
    conn.close()
    
    logger.info(f"Found {len(profiles)} CV profiles to migrate")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for profile in profiles:
        try:
            pg_conn = postgres_db._get_connection()
            pg_cursor = pg_conn.cursor()
            
            # Check if profile already exists
            pg_cursor.execute(
                "SELECT id FROM cv_profiles WHERE cv_id = %s AND user_id = %s", 
                (profile['cv_id'], profile['user_id'])
            )
            if pg_cursor.fetchone():
                skipped += 1
                pg_cursor.close()
                postgres_db._return_connection(pg_conn)
                continue
            
            # Insert CV profile - map SQLite fields to PostgreSQL fields
            # Use parsed_date as both created_date and last_updated
            parsed_date = profile.get('parsed_date', datetime.now().isoformat())
            
            pg_cursor.execute("""
                INSERT INTO cv_profiles (
                    cv_id, user_id, technical_skills, soft_skills, languages,
                    education, work_history, achievements, expertise_summary,
                    career_level, preferred_roles, industries, raw_analysis,
                    created_date, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                profile['cv_id'],
                profile['user_id'],
                profile.get('technical_skills'),
                profile.get('soft_skills'),
                profile.get('languages'),
                profile.get('education'),
                profile.get('work_experience'),  # SQLite uses work_experience, not work_history
                profile.get('career_highlights'),  # Map career_highlights to achievements
                profile.get('expertise_summary'),
                None,  # career_level not in SQLite
                None,  # preferred_roles not in SQLite
                profile.get('industries'),
                profile.get('full_text'),  # Map full_text to raw_analysis
                parsed_date,
                parsed_date
            ))
            
            pg_conn.commit()
            migrated += 1
            
            if migrated % 10 == 0:
                logger.info(f"Migrated {migrated} CV profiles...")
                
            pg_cursor.close()
            postgres_db._return_connection(pg_conn)
            
        except Exception as e:
            errors += 1
            logger.error(f"Error migrating CV profile {profile['id']}: {e}")
            if 'pg_conn' in locals():
                pg_conn.rollback()
                pg_cursor.close()
                postgres_db._return_connection(pg_conn)
    
    logger.info(f"CV profiles migration complete: {migrated} migrated, {skipped} skipped, {errors} errors")
    return (migrated, skipped, errors)


def migrate_all(sqlite_path: str, postgres_url: str):
    """
    Migrate all user data from SQLite to PostgreSQL
    
    Args:
        sqlite_path: Path to SQLite database file
        postgres_url: PostgreSQL connection URL
    """
    logger.info("="*80)
    logger.info("STARTING USER DATA MIGRATION: SQLite → PostgreSQL")
    logger.info(f"Source: {sqlite_path}")
    logger.info(f"Target: {postgres_url[:50]}...")
    logger.info("="*80)
    
    # Initialize databases
    try:
        logger.info("\nConnecting to SQLite database...")
        sqlite_db = CVManager(sqlite_path)
        
        logger.info("Connecting to PostgreSQL database...")
        postgres_db = PostgresDatabase(postgres_url)
        
    except Exception as e:
        logger.error(f"Failed to connect to databases: {e}")
        sys.exit(1)
    
    # Migrate users first (required for foreign keys)
    users_migrated, users_skipped, users_errors = migrate_users(sqlite_db, postgres_db)
    
    # Migrate CVs (depends on users)
    cvs_migrated, cvs_skipped, cvs_errors = migrate_cvs(sqlite_db, postgres_db)
    
    # Migrate CV profiles (depends on users and CVs)
    profiles_migrated, profiles_skipped, profiles_errors = migrate_cv_profiles(sqlite_db, postgres_db)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("MIGRATION COMPLETE")
    logger.info("="*80)
    logger.info(f"\nUsers:")
    logger.info(f"  ✓ Migrated: {users_migrated}")
    logger.info(f"  ⊘ Skipped:  {users_skipped}")
    logger.info(f"  ✗ Errors:   {users_errors}")
    
    logger.info(f"\nCVs:")
    logger.info(f"  ✓ Migrated: {cvs_migrated}")
    logger.info(f"  ⊘ Skipped:  {cvs_skipped}")
    logger.info(f"  ✗ Errors:   {cvs_errors}")
    
    logger.info(f"\nCV Profiles:")
    logger.info(f"  ✓ Migrated: {profiles_migrated}")
    logger.info(f"  ⊘ Skipped:  {profiles_skipped}")
    logger.info(f"  ✗ Errors:   {profiles_errors}")
    
    total_migrated = users_migrated + cvs_migrated + profiles_migrated
    total_errors = users_errors + cvs_errors + profiles_errors
    
    logger.info(f"\nTotal:")
    logger.info(f"  ✓ Migrated: {total_migrated}")
    logger.info(f"  ✗ Errors:   {total_errors}")
    
    if total_errors == 0:
        logger.info("\n✓ Migration completed successfully!")
    else:
        logger.warning(f"\n⚠ Migration completed with {total_errors} errors")
    
    logger.info("="*80)
    
    # Close connections
    postgres_db.close()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_users_to_postgres.py <postgresql_url>")
        print("\nExample:")
        print('  python scripts/migrate_users_to_postgres.py "postgresql://user:pass@host:5432/dbname"')
        print("\nOr with Railway DATABASE_URL:")
        print('  python scripts/migrate_users_to_postgres.py "$DATABASE_URL"')
        sys.exit(1)
    
    postgres_url = sys.argv[1]
    sqlite_path = os.environ.get('DATABASE_PATH', 'data/jobs.db')
    
    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite database not found: {sqlite_path}")
        sys.exit(1)
    
    # Confirm migration
    print(f"\n⚠️  WARNING: This will migrate user data from SQLite to PostgreSQL")
    print(f"   Source: {sqlite_path}")
    print(f"   Target: {postgres_url[:50]}...")
    print(f"\n   This will migrate: users, CVs, and CV profiles")
    print(f"   Existing data in PostgreSQL will be preserved (duplicates skipped)")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled")
        sys.exit(0)
    
    migrate_all(sqlite_path, postgres_url)


if __name__ == "__main__":
    main()
