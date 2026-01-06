
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def print_table_info(conn, table_name):
    cur = conn.cursor()
    print(f"\n--- Table: {table_name} ---")
    try:
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """)
        rows = cur.fetchall()
        for row in rows:
            print(f"{row[0]}: {row[1]}")
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")

def main():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        print_table_info(conn, 'users')
        print_table_info(conn, 'cv_profiles')
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    main()
