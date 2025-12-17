"""
Database Migration Script: Single-User to Multi-User
Migrates existing job database to support multiple users with CVs
"""

import sqlite3
import os
import shutil
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.helpers import load_config
from src.database.cv_operations import CVManager


def backup_database(db_path: str) -> str:
    """
    Create a backup of the existing database

    Args:
        db_path: Path to database file

    Returns:
        Path to backup file
    """
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. No migration needed.")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.replace('.db', f'_backup_{timestamp}.db')

    shutil.copy2(db_path, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def check_migration_needed(db_path: str) -> bool:
    """
    Check if migration is needed (i.e., users table doesn't exist)

    Returns:
        True if migration needed, False otherwise
    """
    if not os.path.exists(db_path):
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if users table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='users'
    """)
    users_table_exists = cursor.fetchone() is not None

    # Check if jobs table has user_id column
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [row[1] for row in cursor.fetchall()]
    has_user_id = 'user_id' in columns

    conn.close()

    needs_migration = not (users_table_exists and has_user_id)
    return needs_migration


def add_user_columns_to_jobs(db_path: str):
    """
    Add user_id and cv_profile_id columns to jobs table

    Args:
        db_path: Path to database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'user_id' not in columns:
        print("Adding user_id column to jobs table...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN user_id INTEGER REFERENCES users(id)")
        print("✓ Added user_id column")

    if 'cv_profile_id' not in columns:
        print("Adding cv_profile_id column to jobs table...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN cv_profile_id INTEGER REFERENCES cv_profiles(id)")
        print("✓ Added cv_profile_id column")

    # Create index
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id)")
        print("✓ Created index on user_id")
    except sqlite3.OperationalError:
        pass  # Index already exists

    conn.commit()
    conn.close()


def create_default_user_from_config(cv_manager: CVManager, config: dict) -> int:
    """
    Create default user from config.yaml profile

    Args:
        cv_manager: CVManager instance
        config: Configuration dictionary

    Returns:
        User ID of default user
    """
    profile = config.get('profile', {})

    # Try to extract email from config or use default
    email = profile.get('email', 'default@localhost')

    # Check if we can use environment variable for better email
    import os
    env_email = os.getenv('USER_EMAIL') or os.getenv('EMAIL_ADDRESS')
    if env_email:
        email = env_email

    print(f"Creating default user with email: {email}")

    user = cv_manager.get_or_create_user(
        email=email,
        name=profile.get('name'),
        current_role=profile.get('current_role'),
        location=profile.get('location'),
        preferences=config.get('preferences', {})
    )

    print(f"✓ Created/found default user (ID: {user['id']})")
    return user['id']


def link_existing_jobs_to_user(db_path: str, user_id: int):
    """
    Link all existing jobs to the default user

    Args:
        db_path: Path to database
        user_id: ID of default user
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count jobs without user_id
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE user_id IS NULL")
    job_count = cursor.fetchone()[0]

    if job_count == 0:
        print("No jobs to migrate")
        conn.close()
        return

    print(f"Linking {job_count} existing jobs to user ID {user_id}...")

    cursor.execute("""
        UPDATE jobs
        SET user_id = ?
        WHERE user_id IS NULL
    """, (user_id,))

    conn.commit()
    conn.close()

    print(f"✓ Linked {job_count} jobs to default user")


def verify_migration(db_path: str):
    """
    Verify migration was successful

    Args:
        db_path: Path to database

    Returns:
        True if verification passed
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("MIGRATION VERIFICATION")
    print("="*60)

    # Check tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('users', 'cvs', 'cv_profiles')
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"✓ Tables created: {', '.join(tables)}")

    # Check user count
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"✓ Users in database: {user_count}")

    # Check jobs have user_id
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE user_id IS NOT NULL")
    jobs_with_user = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE user_id IS NULL")
    jobs_without_user = cursor.fetchone()[0]

    print(f"✓ Jobs with user_id: {jobs_with_user}")
    if jobs_without_user > 0:
        print(f"⚠ Jobs without user_id: {jobs_without_user}")
    else:
        print(f"✓ All jobs linked to users")

    # Check indexes
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_%'
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    print(f"✓ Indexes created: {len(indexes)}")

    conn.close()

    print("="*60)
    print("Migration verification complete!")
    print("="*60 + "\n")

    return jobs_without_user == 0


def migrate_database(db_path: str = "data/jobs.db", config_path: str = "config.yaml"):
    """
    Main migration function

    Args:
        db_path: Path to database file
        config_path: Path to config file
    """
    print("\n" + "="*60)
    print("JOB MONITOR: DATABASE MIGRATION TO MULTI-USER")
    print("="*60 + "\n")

    # Check if migration is needed
    if not check_migration_needed(db_path):
        print("Database already migrated or no migration needed.")
        print("Skipping migration.")
        return

    # Step 1: Backup
    print("Step 1: Creating backup...")
    backup_path = backup_database(db_path)

    # Step 2: Initialize CV Manager (creates new tables)
    print("\nStep 2: Creating new tables...")
    cv_manager = CVManager(db_path)
    print("✓ Created users, cvs, and cv_profiles tables")

    # Step 3: Add columns to jobs table
    print("\nStep 3: Updating jobs table...")
    add_user_columns_to_jobs(db_path)

    # Step 4: Create default user from config
    print("\nStep 4: Creating default user...")
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        print("Using default configuration")
        config = {'profile': {}, 'preferences': {}}

    user_id = create_default_user_from_config(cv_manager, config)

    # Step 5: Link existing jobs to user
    print("\nStep 5: Linking existing jobs to default user...")
    link_existing_jobs_to_user(db_path, user_id)

    # Step 6: Verify migration
    print("\nStep 6: Verifying migration...")
    success = verify_migration(db_path)

    # Close CV manager
    cv_manager.close()

    # Final summary
    print("\n" + "="*60)
    if success:
        print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\nBackup saved at: {backup_path}")
        print(f"Original database updated at: {db_path}")
        print("\nNext steps:")
        print("1. Test the system with: python main.py")
        print("2. Upload your CV with: python scripts/cv_cli.py upload --email your@email.com --file your_cv.pdf")
        print("3. If any issues occur, restore from backup:")
        print(f"   cp {backup_path} {db_path}")
    else:
        print("⚠ MIGRATION COMPLETED WITH WARNINGS")
        print("="*60)
        print("Some jobs may not have been linked to users.")
        print("Please review the output above.")

    print("="*60 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Migrate job database to multi-user')
    parser.add_argument('--db-path', default='data/jobs.db',
                       help='Path to database file')
    parser.add_argument('--config-path', default='config.yaml',
                       help='Path to config file')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if already migrated')

    args = parser.parse_args()

    # Change to project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    if args.force:
        print("Force mode enabled - running migration regardless of current state\n")
        migrate_database(args.db_path, args.config_path)
    else:
        # Check if needed first
        if check_migration_needed(args.db_path):
            migrate_database(args.db_path, args.config_path)
        else:
            print("Database already migrated. Use --force to run anyway.")
