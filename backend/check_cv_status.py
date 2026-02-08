#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()

from src.database.postgres_cv_operations import PostgresCVManager
from src.database.postgres_operations import PostgresDatabase

# Get database URL from environment
db_url = os.getenv('DATABASE_URL')

# Create connection pool
job_db = PostgresDatabase(db_url)
cv_manager = PostgresCVManager(job_db.connection_pool)

# Get user
user = cv_manager.get_user_by_email('trial@trial.com')
if user:
    print(f'\nUser ID: {user["id"]} - {user["email"]}')
    
    # Get all CVs including deleted ones
    conn = cv_manager._get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, file_name, file_hash, status, uploaded_date 
        FROM cvs 
        WHERE user_id = %s
        ORDER BY uploaded_date DESC
        LIMIT 10
    ''', (user['id'],))
    
    cvs = cursor.fetchall()
    print(f'\nAll CVs for user {user["id"]}:')
    if not cvs:
        print('  No CVs found')
    else:
        for cv in cvs:
            hash_str = cv[2][:16] if cv[2] else "None"
            print(f'  ID: {cv[0]}, Name: {cv[1][:40]}, Hash: {hash_str}..., Status: {cv[3]}, Date: {cv[4]}')
    
    cursor.close()
    cv_manager._return_connection(conn)
else:
    print('User not found')
