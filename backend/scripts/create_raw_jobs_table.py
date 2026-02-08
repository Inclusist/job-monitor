#!/usr/bin/env python3
"""
Create raw_jobs_test table for testing custom matching logic

This table will hold ALL jobs from Active Jobs DB without any filtering,
allowing us to build and test our own matching algorithms.
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()

def create_table():
    """Create raw_jobs_test table"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print("Creating raw_jobs_test table...")

    # Drop table if exists
    cursor.execute("DROP TABLE IF EXISTS raw_jobs_test CASCADE")

    # Create table with all Active Jobs DB fields including ALL AI metadata
    cursor.execute("""
        CREATE TABLE raw_jobs_test (
            id SERIAL PRIMARY KEY,

            -- Core job fields
            external_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            description TEXT,
            url TEXT,
            source TEXT,
            source_domain TEXT,
            source_type TEXT,

            -- Dates
            posted_date TIMESTAMP,
            date_validthrough TIMESTAMP,
            discovered_date TIMESTAMP DEFAULT NOW(),
            last_updated TIMESTAMP DEFAULT NOW(),

            -- Employment details
            salary TEXT,
            employment_type TEXT,
            remote BOOLEAN DEFAULT FALSE,

            -- Organization details
            organization_url TEXT,
            organization_logo TEXT,

            -- Location arrays
            locations_derived TEXT[],
            cities_derived TEXT[],
            regions_derived TEXT[],
            counties_derived TEXT[],
            countries_derived TEXT[],
            timezones_derived TEXT[],
            lats_derived NUMERIC[],
            lngs_derived NUMERIC[],

            -- AI-extracted metadata - Basic
            ai_employment_type TEXT[],
            ai_work_arrangement TEXT,
            ai_experience_level TEXT,
            ai_job_language TEXT,
            ai_visa_sponsorship BOOLEAN,
            ai_work_arrangement_office_days INTEGER,
            ai_working_hours INTEGER,

            -- AI-extracted metadata - Skills & Requirements
            ai_key_skills TEXT[],
            ai_keywords TEXT[],
            ai_core_responsibilities TEXT,
            ai_requirements_summary TEXT,
            ai_education_requirements TEXT,

            -- AI-extracted metadata - Benefits & Compensation
            ai_benefits TEXT[],
            ai_salary_currency TEXT,
            ai_salary_minvalue NUMERIC,
            ai_salary_maxvalue NUMERIC,
            ai_salary_value NUMERIC,
            ai_salary_unittext TEXT,

            -- AI-extracted metadata - Industry & Taxonomy
            ai_taxonomies_a TEXT[],  -- Industries

            -- AI-extracted metadata - Remote/Location
            ai_remote_location TEXT[],
            ai_remote_location_derived TEXT[],

            -- AI-extracted metadata - Hiring Manager
            ai_hiring_manager_name TEXT,
            ai_hiring_manager_email_address TEXT,

            -- Raw API response (for debugging/analysis)
            raw_data JSONB,

            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes for common queries
    cursor.execute("""
        CREATE INDEX idx_raw_jobs_posted_date ON raw_jobs_test(posted_date DESC);
        CREATE INDEX idx_raw_jobs_location ON raw_jobs_test USING GIN (to_tsvector('english', location));
        CREATE INDEX idx_raw_jobs_title ON raw_jobs_test USING GIN (to_tsvector('english', title));
        CREATE INDEX idx_raw_jobs_description ON raw_jobs_test USING GIN (to_tsvector('english', description));
        CREATE INDEX idx_raw_jobs_ai_experience_level ON raw_jobs_test(ai_experience_level);
        CREATE INDEX idx_raw_jobs_ai_taxonomies ON raw_jobs_test USING GIN (ai_taxonomies_a);
        CREATE INDEX idx_raw_jobs_ai_work_arrangement ON raw_jobs_test(ai_work_arrangement);
        CREATE INDEX idx_raw_jobs_ai_keywords ON raw_jobs_test USING GIN (ai_keywords);
        CREATE INDEX idx_raw_jobs_ai_key_skills ON raw_jobs_test USING GIN (ai_key_skills);
        CREATE INDEX idx_raw_jobs_cities ON raw_jobs_test USING GIN (cities_derived);
        CREATE INDEX idx_raw_jobs_remote ON raw_jobs_test(remote);
        CREATE INDEX idx_raw_jobs_created_at ON raw_jobs_test(created_at DESC);
    """)

    conn.commit()
    print("✓ Table created successfully!")

    # Show table info
    cursor.execute("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'raw_jobs_test'
        ORDER BY ordinal_position
    """)

    print("\nTable structure:")
    print("=" * 60)
    for col, dtype, max_len in cursor.fetchall():
        len_str = f"({max_len})" if max_len else ""
        print(f"  {col}: {dtype}{len_str}")

    cursor.close()
    conn.close()

    print("\n✓ Ready to load jobs!")

if __name__ == "__main__":
    create_table()
