"""
Database module for job monitoring system
Handles SQLite database operations
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import os


class JobDatabase:
    def __init__(self, db_path: str = "data/jobs.db"):
        """Initialize database connection"""
        self.db_path = db_path
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        
        # Jobs table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                description TEXT,
                url TEXT,
                posted_date TEXT,
                salary TEXT,
                discovered_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                match_score INTEGER,
                match_reasoning TEXT,
                key_alignments TEXT,
                potential_gaps TEXT,
                priority TEXT,
                status TEXT DEFAULT 'new',
                notes TEXT
            )
        """)
        
        # Search history table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_date TEXT NOT NULL,
                source TEXT NOT NULL,
                search_term TEXT,
                location TEXT,
                results_count INTEGER,
                execution_time REAL
            )
        """)
        
        # Application tracking table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                applied_date TEXT NOT NULL,
                cover_letter TEXT,
                status TEXT DEFAULT 'submitted',
                follow_up_date TEXT,
                interview_date TEXT,
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        """)
        
        self.conn.commit()
    
    def add_job(self, job_data: Dict[str, Any]) -> Optional[int]:
        """
        Add a new job to the database
        
        Args:
            job_data: Dictionary containing job information
            
        Returns:
            Job ID if successful, None if job already exists
        """
        try:
            now = datetime.now().isoformat()
            
            self.cursor.execute("""
                INSERT INTO jobs (
                    job_id, source, title, company, location, description, 
                    url, posted_date, salary, discovered_date, last_updated,
                    match_score, match_reasoning, key_alignments, potential_gaps,
                    priority, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data.get('job_id'),
                job_data.get('source'),
                job_data.get('title'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('description'),
                job_data.get('url'),
                job_data.get('posted_date'),
                job_data.get('salary'),
                now,
                now,
                job_data.get('match_score'),
                job_data.get('match_reasoning'),
                json.dumps(job_data.get('key_alignments', [])),
                json.dumps(job_data.get('potential_gaps', [])),
                job_data.get('priority', 'medium'),
                'new'
            ))
            
            self.conn.commit()
            return self.cursor.lastrowid
            
        except sqlite3.IntegrityError:
            # Job already exists
            return None
    
    def job_exists(self, job_id: str) -> bool:
        """Check if a job already exists in database"""
        self.cursor.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,))
        return self.cursor.fetchone() is not None
    
    def get_jobs_by_date(self, date: str, status: str = None) -> List[Dict]:
        """Get all jobs discovered on a specific date"""
        query = "SELECT * FROM jobs WHERE DATE(discovered_date) = ?"
        params = [date]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY match_score DESC"
        
        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_jobs_by_score(self, min_score: int, max_results: int = 20) -> List[Dict]:
        """Get jobs above a minimum match score"""
        self.cursor.execute("""
            SELECT * FROM jobs 
            WHERE match_score >= ? AND status = 'new'
            ORDER BY match_score DESC, discovered_date DESC
            LIMIT ?
        """, (min_score, max_results))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_jobs_by_priority(self, priority: str) -> List[Dict]:
        """Get jobs by priority level"""
        self.cursor.execute("""
            SELECT * FROM jobs 
            WHERE priority = ? AND status = 'new'
            ORDER BY match_score DESC, discovered_date DESC
        """, (priority,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def update_job_status(self, job_id: str, status: str, notes: str = None):
        """Update job status (e.g., 'new', 'reviewed', 'applied', 'rejected')"""
        query = "UPDATE jobs SET status = ?, last_updated = ?"
        params = [status, datetime.now().isoformat()]
        
        if notes:
            query += ", notes = ?"
            params.append(notes)
        
        query += " WHERE job_id = ?"
        params.append(job_id)
        
        self.cursor.execute(query, params)
        self.conn.commit()
    
    def add_search_record(self, source: str, search_term: str, location: str, 
                         results_count: int, execution_time: float):
        """Log a search operation"""
        self.cursor.execute("""
            INSERT INTO search_history (
                search_date, source, search_term, location, results_count, execution_time
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            source,
            search_term,
            location,
            results_count,
            execution_time
        ))
        self.conn.commit()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        # Total jobs
        self.cursor.execute("SELECT COUNT(*) FROM jobs")
        stats['total_jobs'] = self.cursor.fetchone()[0]
        
        # Jobs by status
        self.cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM jobs 
            GROUP BY status
        """)
        stats['by_status'] = {row['status']: row['count'] for row in self.cursor.fetchall()}
        
        # Jobs by priority
        self.cursor.execute("""
            SELECT priority, COUNT(*) as count 
            FROM jobs 
            WHERE status = 'new'
            GROUP BY priority
        """)
        stats['by_priority'] = {row['priority']: row['count'] for row in self.cursor.fetchall()}
        
        # Average match score
        self.cursor.execute("SELECT AVG(match_score) FROM jobs WHERE status = 'new'")
        stats['avg_match_score'] = round(self.cursor.fetchone()[0] or 0, 2)
        
        return stats
    
    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == "__main__":
    # Test the database
    db = JobDatabase("data/jobs.db")
    
    # Test adding a job
    test_job = {
        'job_id': 'test_001',
        'source': 'indeed',
        'title': 'Head of Data Science',
        'company': 'Test Company',
        'location': 'Berlin, Germany',
        'description': 'Test description',
        'url': 'https://example.com/job',
        'posted_date': '2024-12-16',
        'match_score': 85,
        'match_reasoning': 'Strong match',
        'key_alignments': ['Leadership', 'AI/ML'],
        'potential_gaps': ['Specific domain knowledge'],
        'priority': 'high'
    }
    
    job_id = db.add_job(test_job)
    print(f"Added job with ID: {job_id}")
    
    # Get statistics
    stats = db.get_statistics()
    print(f"Database statistics: {stats}")
    
    db.close()
    print("Database test completed successfully!")
