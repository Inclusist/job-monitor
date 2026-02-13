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
        
        # Don't store connection - create on demand for thread safety
        self._create_tables()
    
    def _get_connection(self):
        """Get a thread-safe database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Jobs table
        cursor.execute("""
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
        cursor.execute("""
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
        cursor.execute("""
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
        
        # Job feedback table for learning user preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                match_score_original INTEGER,
                match_score_user INTEGER,
                feedback_reason TEXT,
                created_date TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        """)
        
        # User-Job matches table (junction table for per-user scoring)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_job_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                semantic_score INTEGER,
                semantic_date TEXT,
                claude_score INTEGER,
                claude_date TEXT,
                priority TEXT,
                match_reasoning TEXT,
                key_alignments TEXT,
                potential_gaps TEXT,
                status TEXT DEFAULT 'new',
                created_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE(user_id, job_id)
            )
        """)
        
        # Indexes for user_job_matches
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_job_matches_user ON user_job_matches(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_job_matches_job ON user_job_matches(job_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_job_matches_scores ON user_job_matches(user_id, semantic_score, claude_score)
        """)

        # Tool feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ratings TEXT NOT NULL,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
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
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO jobs (
                    job_id, source, title, company, location, description, 
                    url, posted_date, salary, discovered_date, last_updated,
                    match_score, match_reasoning, key_alignments, potential_gaps,
                    priority, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data.get('job_id') or job_data.get('external_id'),  # Support both field names
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
                job_data.get('match_reasoning') or job_data.get('reasoning'),  # Support both field names
                json.dumps(job_data.get('key_alignments', [])),
                json.dumps(job_data.get('potential_gaps', [])),
                job_data.get('priority', 'medium'),
                'new'
            ))
            
            conn.commit()
            job_id = cursor.lastrowid
            conn.close()
            return job_id
            
        except sqlite3.IntegrityError:
            # Job already exists
            return None
            return None
    
    def job_exists(self, job_id: str) -> bool:
        """Check if a job already exists in database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def get_jobs_by_date(self, date: str, status: str = None) -> List[Dict]:
        """Get all jobs discovered on a specific date"""
        query = "SELECT * FROM jobs WHERE DATE(discovered_date) = ?"
        params = [date]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY match_score DESC"
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_jobs_by_score(self, min_score: int, max_results: int = 20) -> List[Dict]:
        """Get jobs above a minimum match score (excludes deleted jobs)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE match_score >= ? AND status != 'deleted'
            ORDER BY match_score DESC, discovered_date DESC
            LIMIT ?
        """, (min_score, max_results))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_jobs_by_priority(self, priority: str) -> List[Dict]:
        """Get jobs by priority level (excludes deleted jobs)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE priority = ? AND status != 'deleted'
            ORDER BY match_score DESC, discovered_date DESC
        """, (priority,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_jobs_discovered_today(self) -> List[Dict]:
        """Get jobs discovered today (excludes deleted jobs)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE DATE(discovered_date) = DATE('now') AND status != 'deleted'
            ORDER BY COALESCE(match_score, 0) DESC
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_jobs_discovered_before_today(self, limit: int = 50) -> List[Dict]:
        """Get jobs discovered before today (excludes deleted jobs)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE DATE(discovered_date) < DATE('now') AND status != 'deleted'
            ORDER BY COALESCE(match_score, 0) DESC, discovered_date DESC
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def update_job_status(self, job_id: str, status: str, notes: str = None):
        """
        Update job status (e.g., 'new', 'reviewed', 'applied', 'rejected')
        
        Args:
            job_id: Can be either the database id (integer) or job_id (string)
            status: New status value
            notes: Optional notes
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if job_id is an integer (database id) or string (job_id)
        if isinstance(job_id, int) or (isinstance(job_id, str) and job_id.isdigit()):
            # It's a database id
            query = "UPDATE jobs SET status = ?, last_updated = ?"
            params = [status, datetime.now().isoformat()]
            
            if notes:
                query += ", notes = ?"
                params.append(notes)
            
            query += " WHERE id = ?"
            params.append(int(job_id))
        else:
            # It's a job_id string
            query = "UPDATE jobs SET status = ?, last_updated = ?"
            params = [status, datetime.now().isoformat()]
            
            if notes:
                query += ", notes = ?"
                params.append(notes)
            
            query += " WHERE job_id = ?"
            params.append(job_id)
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
    
    def get_deleted_job_ids(self) -> set:
        """
        Get set of job_ids that have been deleted/hidden
        Used to prevent re-adding deleted jobs in future searches
        
        Returns:
            Set of job_id strings for deleted jobs
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT job_id FROM jobs WHERE status = "deleted"')
        deleted_ids = {row[0] for row in cursor.fetchall()}
        conn.close()
        return deleted_ids
    
    def get_deleted_jobs(self, limit: int = 50) -> List[Dict]:
        """
        Get all deleted/hidden jobs
        
        Args:
            limit: Maximum number of deleted jobs to return
            
        Returns:
            List of deleted job dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE status = 'deleted'
            ORDER BY last_updated DESC
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def permanently_delete_job(self, job_id: int) -> bool:
        """
        Permanently remove a job from the database
        Warning: This cannot be undone!
        
        Args:
            job_id: Database ID of the job
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error permanently deleting job: {e}")
            return False
    
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
        conn = self._get_connection()
        cursor = conn.cursor()
        stats = {}
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM jobs")
        stats['total_jobs'] = cursor.fetchone()[0]
        
        # Jobs by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM jobs 
            GROUP BY status
        """)
        stats['by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Jobs by priority (exclude deleted)
        cursor.execute("""
            SELECT priority, COUNT(*) as count 
            FROM jobs 
            WHERE status != 'deleted'
            GROUP BY priority
        """)
        stats['by_priority'] = {row['priority']: row['count'] for row in cursor.fetchall()}
        
        # Count hidden jobs
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'deleted'")
        stats['hidden_jobs'] = cursor.fetchone()[0]
        
        # Average match score (exclude deleted)
        cursor.execute("SELECT AVG(match_score) FROM jobs WHERE status != 'deleted'")
        stats['avg_match_score'] = round(cursor.fetchone()[0] or 0, 2)
        
        conn.close()
        return stats
    
    def add_feedback(self, job_id: int, user_email: str, feedback_type: str, 
                     match_score_original: int, match_score_user: Optional[int] = None,
                     feedback_reason: Optional[str] = None) -> bool:
        """
        Add user feedback on a job match score
        
        Args:
            job_id: Database ID of the job
            user_email: User providing feedback
            feedback_type: 'agree', 'disagree', 'too_high', 'too_low'
            match_score_original: Original Claude match score
            match_score_user: User's suggested match score (optional)
            feedback_reason: Optional explanation from user
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO job_feedback (
                    job_id, user_email, feedback_type, match_score_original,
                    match_score_user, feedback_reason, created_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, user_email, feedback_type, match_score_original,
                match_score_user, feedback_reason, datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error adding feedback: {e}")
            return False
    
    def get_user_feedback(self, user_email: str, limit: int = 50) -> List[Dict]:
        """
        Get user's feedback history
        
        Args:
            user_email: User email
            limit: Maximum number of feedback records to return
            
        Returns:
            List of feedback records with job details
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                f.id, f.job_id, f.feedback_type, f.match_score_original,
                f.match_score_user, f.feedback_reason, f.created_date,
                j.title, j.company, j.location, j.description,
                j.key_alignments, j.potential_gaps
            FROM job_feedback f
            JOIN jobs j ON f.job_id = j.id
            WHERE f.user_email = ?
            ORDER BY f.created_date DESC
            LIMIT ?
        """, (user_email, limit))
        
        rows = cursor.fetchall()
        feedback = []
        
        for row in rows:
            feedback.append({
                'id': row[0],
                'job_id': row[1],
                'feedback_type': row[2],
                'match_score_original': row[3],
                'match_score_user': row[4],
                'feedback_reason': row[5],
                'created_date': row[6],
                'job_title': row[7],
                'job_company': row[8],
                'job_location': row[9],
                'job_description': row[10],
                'key_alignments': row[11],
                'potential_gaps': row[12]
            })
        
        conn.close()
        return feedback

    def add_tool_feedback(self, user_id: int, ratings: dict, comment: str) -> bool:
        """Add general feedback about the tool with multiple ratings"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            import json
            cursor.execute("""
                INSERT INTO tool_feedback (user_id, ratings, comment)
                VALUES (?, ?, ?)
            """, (user_id, json.dumps(ratings), comment))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding tool feedback: {e}")
            return False
    
    def get_shortlisted_jobs(self, user_email: str = 'default@localhost') -> List[Dict]:
        """
        Get jobs marked as 'shortlisted' or 'applying'
        
        Args:
            user_email: User email (for multi-user support)
            
        Returns:
            List of shortlisted job dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE status IN ('shortlisted', 'applying')
            ORDER BY match_score DESC, discovered_date DESC
        """)
        
        rows = cursor.fetchall()
        jobs = []
        
        for row in rows:
            jobs.append({
                'id': row['id'],
                'job_id': row['job_id'],
                'source': row['source'],
                'title': row['title'],
                'company': row['company'],
                'location': row['location'],
                'description': row['description'],
                'url': row['url'],
                'posted_date': row['posted_date'],
                'salary': row['salary'],
                'discovered_date': row['discovered_date'],
                'last_updated': row['last_updated'],
                'match_score': row['match_score'],
                'match_reasoning': row['match_reasoning'],
                'key_alignments': row['key_alignments'],
                'potential_gaps': row['potential_gaps'],
                'priority': row['priority'],
                'status': row['status'],
                'notes': row['notes']
            })
        
        conn.close()
        return jobs
    
    # ==================== User Job Matches ====================
    
    def add_user_job_match(self, user_id: int, job_id: int, semantic_score: int = None,
                           claude_score: int = None, priority: str = None,
                           match_reasoning: str = None, key_alignments: list = None,
                           potential_gaps: list = None) -> bool:
        """
        Add or update a user-job match with scores
        
        Args:
            user_id: User ID
            job_id: Job ID
            semantic_score: Semantic similarity score (0-100)
            claude_score: Claude analysis score (0-100)
            priority: high/medium/low
            match_reasoning: Explanation text
            key_alignments: List of alignments
            potential_gaps: List of gaps
            
        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            # Check if match already exists
            cursor.execute("""
                SELECT id FROM user_job_matches 
                WHERE user_id = ? AND job_id = ?
            """, (user_id, job_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing match
                updates = []
                values = []
                
                if semantic_score is not None:
                    updates.append("semantic_score = ?")
                    updates.append("semantic_date = ?")
                    values.extend([semantic_score, now])
                
                if claude_score is not None:
                    updates.append("claude_score = ?")
                    updates.append("claude_date = ?")
                    values.extend([claude_score, now])
                
                if priority is not None:
                    updates.append("priority = ?")
                    values.append(priority)
                
                if match_reasoning is not None:
                    updates.append("match_reasoning = ?")
                    values.append(match_reasoning)
                
                if key_alignments is not None:
                    import json
                    updates.append("key_alignments = ?")
                    values.append(json.dumps(key_alignments) if key_alignments else '[]')
                
                if potential_gaps is not None:
                    import json
                    updates.append("potential_gaps = ?")
                    values.append(json.dumps(potential_gaps) if potential_gaps else '[]')
                
                updates.append("last_updated = ?")
                values.append(now)
                values.append(existing['id'])
                
                cursor.execute(f"""
                    UPDATE user_job_matches 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)
            else:
                # Insert new match
                import json
                cursor.execute("""
                    INSERT INTO user_job_matches (
                        user_id, job_id, semantic_score, semantic_date,
                        claude_score, claude_date, priority, match_reasoning,
                        key_alignments, potential_gaps, created_date, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, job_id,
                    semantic_score, now if semantic_score is not None else None,
                    claude_score, now if claude_score is not None else None,
                    priority, match_reasoning,
                    json.dumps(key_alignments) if key_alignments else '[]',
                    json.dumps(potential_gaps) if potential_gaps else '[]',
                    now, now
                ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding user job match: {e}")
            conn.close()
            return False
    
    def get_user_job_matches(self, user_id: int, min_semantic_score: int = None,
                            min_claude_score: int = None, status: str = None,
                            limit: int = None) -> List[Dict]:
        """
        Get job matches for a user with optional filtering
        
        Args:
            user_id: User ID
            min_semantic_score: Minimum semantic score
            min_claude_score: Minimum Claude score
            status: Filter by status
            limit: Maximum results
            
        Returns:
            List of matches with job details
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                ujm.*,
                j.id as job_table_id,
                j.job_id as external_id, 
                j.source, 
                j.title, 
                j.company, 
                j.location as job_location,
                j.description, 
                j.url, 
                j.posted_date, 
                j.salary,
                j.discovered_date
            FROM user_job_matches ujm
            JOIN jobs j ON ujm.job_id = j.id
            WHERE ujm.user_id = ?
        """
        params = [user_id]
        
        if min_semantic_score is not None:
            query += " AND ujm.semantic_score >= ?"
            params.append(min_semantic_score)
        
        if min_claude_score is not None:
            query += " AND ujm.claude_score >= ?"
            params.append(min_claude_score)
        
        if status:
            query += " AND ujm.status = ?"
            params.append(status)
        
        query += " ORDER BY COALESCE(ujm.claude_score, ujm.semantic_score, 0) DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        matches = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return matches
    
    def get_unfiltered_jobs_for_user(self, user_id: int) -> List[Dict]:
        """
        Get jobs that haven't been filtered yet for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            List of job dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get jobs that don't have a match entry for this user
        cursor.execute("""
            SELECT j.*
            FROM jobs j
            LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = ?
            WHERE ujm.id IS NULL
            ORDER BY j.discovered_date DESC
        """, (user_id,))
        
        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Parse JSON fields
        for job in jobs:
            for field in ['key_responsibilities', 'requirements', 'benefits']:
                if job.get(field):
                    try:
                        job[field] = json.loads(job[field])
                    except:
                        pass
        
        return jobs
    
    def count_new_jobs_since(self, user_id: int, since_date: str) -> int:
        """
        Count jobs added since a given date that haven't been matched for this user
        
        Args:
            user_id: User ID
            since_date: ISO date string
            
        Returns:
            Count of new jobs
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM jobs j
            LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = ?
            WHERE j.discovered_date > ? AND ujm.id IS NULL
        """, (user_id, since_date))
        
        count = cursor.fetchone()['count']
        conn.close()
        
        return count
    
    def close(self):
        """Close database connection (thread-safe connections are auto-closed)"""
        # With thread-safe connections, we don't need to maintain a persistent connection
        pass


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
