
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment.")
    sys.exit(1)

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        print("Connected to database.")
        
        # List all tables
        print("\nTables in database:")
        result = connection.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result.fetchall()]
        for t in tables:
            print(f" - {t}")

        if 'jobs' in tables:
            # Check total count
            result = connection.execute(text("SELECT COUNT(*) FROM jobs"))
            total_count = result.scalar()
            print(f"\nTotal rows in 'jobs': {total_count}")
            
            # Get columns
            result = connection.execute(text("SELECT * FROM jobs LIMIT 1"))
            columns = result.keys()
            print(f"Columns in 'jobs': {list(columns)}")

            if 'source_type' in columns:
                # Get a sample "Good" row
                print("\n=== SAMPLE ENRICHED JOB (Truth for Learning) ===")
                query = text("SELECT * FROM jobs WHERE source_type IS NOT NULL AND ai_key_skills IS NOT NULL LIMIT 1")
                row_proxy = connection.execute(query).fetchone()
                
                if row_proxy:
                    # Convert to dict to print keys and values clearly
                    row_dict = row_proxy._asdict()
                    for k, v in row_dict.items():
                        # specific interest in ai_ fields
                        if k.startswith('ai_') or k in ['source_type']:
                            print(f"{k}: {v} (Type: {type(v).__name__})")
                else:
                    print("Could not find a good example row.")


except Exception as e:
    print(f"Error: {e}")
