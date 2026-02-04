#!/usr/bin/env python3
"""
Backfill resume_pdf_data for existing resumes.

Regenerates PDFs from stored resume_html using WeasyPrint and writes the
bytes directly into the resume_pdf_data column.  Skips resumes that already
have pdf_data populated.

Usage:
    python scripts/migrations/backfill_pdf_data.py
"""
import os
import sys
import io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2


def run_backfill():
    from weasyprint import HTML

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = False
    cursor = conn.cursor()

    print("=" * 70)
    print("BACKFILL resume_pdf_data")
    print("=" * 70)
    print()

    cursor.execute("""
        SELECT id, resume_html
        FROM user_generated_resumes
        WHERE resume_pdf_data IS NULL AND resume_html IS NOT NULL
        ORDER BY id
    """)
    rows = cursor.fetchall()
    print(f"   Resumes needing PDF: {len(rows)}")

    done = 0
    for resume_id, html in rows:
        try:
            buf = io.BytesIO()
            HTML(string=html).write_pdf(buf)
            pdf_bytes = buf.getvalue()

            cursor.execute(
                "UPDATE user_generated_resumes SET resume_pdf_data = %s WHERE id = %s",
                (psycopg2.Binary(pdf_bytes), resume_id),
            )
            conn.commit()
            done += 1
            print(f"   id={resume_id}: {len(pdf_bytes):,} bytes")
        except Exception as e:
            conn.rollback()
            print(f"   id={resume_id}: FAILED — {e}")

    print()
    print(f"   Done: {done}/{len(rows)} backfilled")
    print("=" * 70)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    run_backfill()
