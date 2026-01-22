#!/usr/bin/env python3
"""
Script to regenerate PDF for an existing resume

Usage:
    python scripts/regenerate_resume_pdf.py <job_id> [user_email]

Example:
    python scripts/regenerate_resume_pdf.py 23867
    python scripts/regenerate_resume_pdf.py 23867 user@example.com
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_resume_operations import PostgresResumeOperations
from src.database.postgres_cv_manager import PostgresCVManager
from src.resume.resume_generator import ResumeGenerator
from psycopg2.pool import SimpleConnectionPool

def regenerate_pdf(job_id: int, user_email: str = None):
    """
    Regenerate PDF for a resume

    Args:
        job_id: Job ID for the resume
        user_email: Optional user email (if not provided, will find first matching resume)
    """

    DATABASE_URL = os.getenv('DATABASE_URL')

    if not DATABASE_URL or not DATABASE_URL.startswith('postgres'):
        print("❌ Error: DATABASE_URL not set or not PostgreSQL")
        return False

    print(f"🔗 Connecting to database...")

    # Create connection pool
    pool = SimpleConnectionPool(1, 5, DATABASE_URL)

    try:
        # Initialize resume operations
        resume_ops = PostgresResumeOperations(pool)
        cv_manager = PostgresCVManager(pool)

        # Initialize resume generator
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            print("❌ Error: ANTHROPIC_API_KEY not set")
            return False

        resume_gen = ResumeGenerator(anthropic_api_key)

        # Get user ID if email provided
        user_id = None
        if user_email:
            user = cv_manager.get_user_by_email(user_email)
            if user:
                user_id = user['id']
                print(f"✓ Found user: {user_email} (ID: {user_id})")
            else:
                print(f"❌ User not found: {user_email}")
                return False

        # Find the resume
        print(f"\n🔍 Looking for resume for job ID {job_id}...")

        conn = pool.getconn()
        try:
            cur = conn.cursor()

            if user_id:
                cur.execute("""
                    SELECT id, user_id, job_id, resume_html, resume_pdf_path
                    FROM user_generated_resumes
                    WHERE job_id = %s AND user_id = %s
                    LIMIT 1
                """, (job_id, user_id))
            else:
                cur.execute("""
                    SELECT id, user_id, job_id, resume_html, resume_pdf_path
                    FROM user_generated_resumes
                    WHERE job_id = %s
                    LIMIT 1
                """, (job_id,))

            resume_row = cur.fetchone()

            if not resume_row:
                print(f"❌ No resume found for job ID {job_id}")
                if user_id:
                    print(f"   (searched for user ID {user_id})")
                return False

            resume_id, found_user_id, found_job_id, resume_html, old_pdf_path = resume_row

            print(f"✓ Found resume ID {resume_id} for user ID {found_user_id}")
            print(f"  Old PDF path: {old_pdf_path or 'None'}")

            # Generate PDF
            print(f"\n📄 Generating PDF...")

            # Create PDF directory if it doesn't exist
            pdf_dir = Path('data/resumes')
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Create PDF path
            pdf_filename = f"resume_{found_user_id}_{found_job_id}.pdf"
            pdf_path = pdf_dir / pdf_filename

            # Generate PDF from HTML
            try:
                resume_gen.html_to_pdf(resume_html, str(pdf_path))
                print(f"✓ PDF generated: {pdf_path}")
            except Exception as e:
                print(f"❌ Error generating PDF: {e}")
                import traceback
                traceback.print_exc()
                return False

            # Update database with PDF path
            print(f"\n💾 Updating database...")

            cur.execute("""
                UPDATE user_generated_resumes
                SET resume_pdf_path = %s
                WHERE id = %s
            """, (str(pdf_path), resume_id))

            conn.commit()

            print(f"✓ Database updated")
            print(f"\n✅ Success! PDF regenerated for resume ID {resume_id}")
            print(f"   Job ID: {found_job_id}")
            print(f"   User ID: {found_user_id}")
            print(f"   PDF location: {pdf_path}")

            # Verify file exists
            if pdf_path.exists():
                file_size = pdf_path.stat().st_size
                print(f"   File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")

            return True

        finally:
            pool.putconn(conn)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        pool.closeall()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/regenerate_resume_pdf.py <job_id> [user_email]")
        print("\nExamples:")
        print("  python scripts/regenerate_resume_pdf.py 23867")
        print("  python scripts/regenerate_resume_pdf.py 23867 user@example.com")
        sys.exit(1)

    job_id = int(sys.argv[1])
    user_email = sys.argv[2] if len(sys.argv) > 2 else None

    print("=" * 70)
    print(f"Regenerating PDF for Job ID: {job_id}")
    if user_email:
        print(f"User Email: {user_email}")
    print("=" * 70)

    success = regenerate_pdf(job_id, user_email)

    if success:
        print("\n" + "=" * 70)
        print("✅ PDF regeneration completed successfully!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ PDF regeneration failed!")
        print("=" * 70)
        sys.exit(1)
