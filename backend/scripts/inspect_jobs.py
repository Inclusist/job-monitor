import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add project root to path to ensure we can import if needed, 
# though we are mostly using standard libs and installed packages.
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment, using the one read previously.")
    DATABASE_URL = "postgresql://postgres:CYHmwJUlRzLDqflcKrwVJgNpFnijNcIV@centerbeam.proxy.rlwy.net:28639/railway"

print(f"Connecting to: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        print("Connected successfully.")
        
        # Check if table exists first (optional but good for debugging)
        # But user asked to look at jobs table, so we assume it exists.
        
        query = text("SELECT * FROM jobs LIMIT 5;")
        result = connection.execute(query)
        rows = result.fetchall()
        
        if not rows:
             print("No jobs found in the 'jobs' table.")
        else:
             print(f"Successfully retrieved rows. Found {len(rows)} (showing first 5).")
             # Print header
             keys = result.keys()
             print(f"Columns: {list(keys)}")
             print("-" * 50)
             for row in rows:
                 print(row)
                 print("-" * 50)

except Exception as e:
    print(f"Error: {e}")
