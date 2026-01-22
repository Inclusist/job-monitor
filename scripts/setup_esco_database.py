#!/usr/bin/env python3
"""
Setup ESCO Skills Database

Downloads ESCO (European Skills, Competences, Qualifications and Occupations) taxonomy
and creates a PostgreSQL table for standardized skill matching.

ESCO provides ~13,700 standardized skills with:
- Unique URIs
- Multilingual labels
- Hierarchical relationships
- Descriptions
"""

import os
import sys
import json
import requests
import psycopg2
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


def download_esco_data():
    """
    Download ESCO skills and competences from the official portal

    ESCO Portal: https://esco.ec.europa.eu/en/use-esco/download
    """
    print("📥 Checking for ESCO skills & competences taxonomy...")

    os.makedirs("data", exist_ok=True)
    csv_path = "data/skills_en.csv"

    # Check if file already exists
    if os.path.exists(csv_path):
        file_size = os.path.getsize(csv_path) / (1024 * 1024)  # MB
        print(f"  ✓ Found existing file: {csv_path} ({file_size:.2f} MB)")
        return csv_path

    # ESCO no longer provides direct download URLs - manual download required
    print("\n" + "=" * 70)
    print("⚠️  Manual Download Required")
    print("=" * 70)
    print("\nESCO has changed their download system. Please follow these steps:\n")
    print("1. Visit: https://esco.ec.europa.eu/en/use-esco/download")
    print("2. Select:")
    print("   - Version: ESCO v1.2.1 (or latest)")
    print("   - Content: Classification")
    print("   - Language: English")
    print("   - File type: CSV")
    print("3. Accept privacy statement and provide email")
    print("4. Download the CSV package (you'll receive a link via email)")
    print("5. Extract the CSV files and locate 'skills_en.csv'")
    print(f"6. Copy 'skills_en.csv' to: {os.path.abspath(csv_path)}")
    print("\nAfter placing the file, run this script again.")
    print("=" * 70 + "\n")

    sys.exit(1)


def parse_esco_csv(csv_path):
    """Parse ESCO CSV file"""
    import csv

    print("📊 Parsing ESCO CSV...")

    items = []
    stats = {'skill': 0, 'competence': 0, 'knowledge': 0, 'other': 0}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            skill_type = row.get('skillType', '').lower()

            item = {
                'uri': row.get('conceptUri', ''),
                'preferred_label': row.get('preferredLabel', ''),
                'alt_labels': row.get('altLabels', '').split('\n') if row.get('altLabels') else [],
                'description': row.get('description', ''),
                'skill_type': skill_type,  # 'skill', 'competence', 'knowledge', etc.
                'reuse_level': row.get('reuseLevel', ''),  # 'transversal', 'sector-specific', 'occupation-specific'
            }

            if item['uri'] and item['preferred_label']:
                items.append(item)

                # Count by type
                if 'skill' in skill_type:
                    stats['skill'] += 1
                elif 'competence' in skill_type or 'competency' in skill_type:
                    stats['competence'] += 1
                elif 'knowledge' in skill_type:
                    stats['knowledge'] += 1
                else:
                    stats['other'] += 1

    print(f"  ✓ Parsed {len(items)} items:")
    print(f"    - Skills: {stats['skill']}")
    print(f"    - Competences: {stats['competence']}")
    print(f"    - Knowledge: {stats['knowledge']}")
    print(f"    - Other: {stats['other']}")

    return items


def create_esco_table(conn):
    """Create ESCO skills/competences table in PostgreSQL"""
    print("🗄️  Creating ESCO skills & competences table...")

    cur = conn.cursor()

    # Drop existing table if it exists
    cur.execute("DROP TABLE IF EXISTS esco_skills CASCADE")

    # Create table (stores both skills AND competences)
    cur.execute("""
        CREATE TABLE esco_skills (
            id SERIAL PRIMARY KEY,
            uri TEXT UNIQUE NOT NULL,
            preferred_label TEXT NOT NULL,
            alt_labels TEXT[],
            description TEXT,
            skill_type TEXT,  -- 'skill', 'competence', 'knowledge', etc.
            reuse_level TEXT,  -- 'transversal', 'sector-specific', 'occupation-specific'
            search_vector tsvector,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for fast searching
    cur.execute("""
        CREATE INDEX idx_esco_uri ON esco_skills(uri)
    """)

    cur.execute("""
        CREATE INDEX idx_esco_label ON esco_skills(preferred_label)
    """)

    cur.execute("""
        CREATE INDEX idx_esco_type ON esco_skills(skill_type)
    """)

    # Create full-text search index
    cur.execute("""
        CREATE INDEX idx_esco_search ON esco_skills USING GIN(search_vector)
    """)

    conn.commit()
    print("  ✓ Table created (stores both skills and competences)")


def insert_esco_skills(conn, items):
    """Insert ESCO skills/competences into database"""
    print("💾 Inserting ESCO skills & competences into database...")

    cur = conn.cursor()

    # Prepare batch insert
    insert_query = """
        INSERT INTO esco_skills (uri, preferred_label, alt_labels, description, skill_type, reuse_level, search_vector)
        VALUES (%s, %s, %s, %s, %s, %s, to_tsvector('english', %s || ' ' || COALESCE(%s, '')))
        ON CONFLICT (uri) DO UPDATE SET
            preferred_label = EXCLUDED.preferred_label,
            alt_labels = EXCLUDED.alt_labels,
            description = EXCLUDED.description,
            skill_type = EXCLUDED.skill_type,
            reuse_level = EXCLUDED.reuse_level,
            search_vector = EXCLUDED.search_vector
    """

    batch_size = 100
    inserted = 0

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]

        for item in batch:
            # Combine preferred label and alt labels for search
            search_text = item['preferred_label'] + ' ' + ' '.join(item['alt_labels'])

            cur.execute(insert_query, (
                item['uri'],
                item['preferred_label'],
                item['alt_labels'],
                item['description'],
                item['skill_type'],
                item['reuse_level'],
                item['preferred_label'] + ' ' + ' '.join(item['alt_labels']),
                item['description']
            ))

        inserted += len(batch)
        print(f"  Progress: {inserted}/{len(items)}", end='\r')

    conn.commit()
    print(f"\n  ✓ Inserted {inserted} items")


def create_skill_mapping_table(conn):
    """
    Create table to store mappings from extracted skills to ESCO skills
    """
    print("🗄️  Creating skill mapping table...")

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS skill_mappings (
            id SERIAL PRIMARY KEY,
            extracted_text TEXT NOT NULL,
            esco_uri TEXT NOT NULL REFERENCES esco_skills(uri),
            confidence FLOAT,
            source TEXT,  -- 'job', 'cv', etc.
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(extracted_text, esco_uri)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_skill_mappings_text ON skill_mappings(extracted_text)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_skill_mappings_esco ON skill_mappings(esco_uri)
    """)

    conn.commit()
    print("  ✓ Mapping table created")


def main():
    """Main setup function"""
    print("=" * 70)
    print("ESCO Skills Database Setup")
    print("=" * 70)
    print()

    DATABASE_URL = os.getenv('DATABASE_URL')

    if not DATABASE_URL or not DATABASE_URL.startswith('postgres'):
        print("❌ Error: DATABASE_URL not set or not PostgreSQL")
        return False

    try:
        # Download ESCO data
        csv_path = download_esco_data()

        # Parse CSV
        items = parse_esco_csv(csv_path)

        # Connect to database
        print(f"\n🔗 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)

        # Create tables
        create_esco_table(conn)
        create_skill_mapping_table(conn)

        # Insert skills & competences
        insert_esco_skills(conn, items)

        # Verify and show statistics
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM esco_skills")
        total_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM esco_skills WHERE skill_type LIKE '%skill%'")
        skill_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM esco_skills WHERE skill_type LIKE '%competence%' OR skill_type LIKE '%competency%'")
        competence_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM esco_skills WHERE skill_type LIKE '%knowledge%'")
        knowledge_count = cur.fetchone()[0]

        print(f"\n✅ Setup complete!")
        print(f"   Total ESCO items in database: {total_count:,}")
        print(f"   - Skills: {skill_count:,}")
        print(f"   - Competences: {competence_count:,}")
        print(f"   - Knowledge: {knowledge_count:,}")
        print()
        print("Next steps:")
        print("  1. Update job/CV parsing to map to ESCO skills & competences")
        print("  2. Use ESCO URIs for matching instead of text")
        print("  3. Enable multilingual support (ESCO supports 27 EU languages)")
        print()
        print("Examples:")
        cur.execute("SELECT preferred_label, skill_type FROM esco_skills WHERE skill_type LIKE '%competence%' LIMIT 5")
        print("  Sample competences:")
        for row in cur.fetchall():
            print(f"    - {row[0]} ({row[1]})")

        cur.execute("SELECT preferred_label, skill_type FROM esco_skills WHERE skill_type LIKE '%skill%' LIMIT 5")
        print("  Sample skills:")
        for row in cur.fetchall():
            print(f"    - {row[0]} ({row[1]})")

        conn.close()
        return True

    except requests.RequestException as e:
        print(f"\n❌ Error downloading ESCO data: {e}")
        print("   You may need to download manually from:")
        print("   https://ec.europa.eu/esco/portal/download")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
