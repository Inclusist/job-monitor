"""
PostgreSQL database operations for job monitoring system
Compatible interface with SQLite operations
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import os
import logging

logger = logging.getLogger(__name__)


class PostgresDatabase:
    """PostgreSQL database operations - compatible with JobDatabase interface"""
    
    def __init__(self, database_url: str):
        """
        Initialize PostgreSQL connection pool
        
        Args:
            database_url: PostgreSQL connection string (e.g., from Railway DATABASE_URL)
        """
        self.database_url = database_url
        
        # Create connection pool for better performance
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=database_url
            )
            logger.info("PostgreSQL connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {e}")
            raise
        
        self._create_tables()
    
    def _get_connection(self):
        """Get a connection from the pool"""
        return self.connection_pool.getconn()
    
    def _return_connection(self, conn):
        """Return connection to pool"""
        self.connection_pool.putconn(conn)
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY,
                    job_id TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    description TEXT,
                    url TEXT,
                    posted_date TIMESTAMP,
                    salary TEXT,
                    discovered_date TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
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
                    id SERIAL PRIMARY KEY,
                    search_date TIMESTAMP NOT NULL,
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
                    id SERIAL PRIMARY KEY,
                    job_id INTEGER NOT NULL,
                    applied_date TIMESTAMP NOT NULL,
                    cover_letter TEXT,
                    status TEXT DEFAULT 'submitted',
                    follow_up_date TIMESTAMP,
                    interview_date TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
                )
            """)
            
            # Job feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_feedback (
                    id SERIAL PRIMARY KEY,
                    job_id INTEGER NOT NULL,
                    user_email TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    match_score_original INTEGER,
                    match_score_user INTEGER,
                    feedback_reason TEXT,
                    created_date TIMESTAMP NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
                )
            """)
            
            # User-Job matches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_job_matches (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    job_id INTEGER NOT NULL,
                    semantic_score INTEGER,
                    semantic_date TIMESTAMP,
                    claude_score INTEGER,
                    claude_date TIMESTAMP,
                    priority TEXT,
                    match_reasoning TEXT,
                    key_alignments TEXT,
                    potential_gaps TEXT,
                    status TEXT DEFAULT 'new',
                    created_date TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    CONSTRAINT unique_user_job UNIQUE(user_id, job_id)
                )
            """)
            
            # Indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_job_matches_user 
                ON user_job_matches(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_job_matches_job 
                ON user_job_matches(job_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_job_matches_scores 
                ON user_job_matches(user_id, semantic_score, claude_score)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_job_id 
                ON jobs(job_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_source 
                ON jobs(source)
            """)
            
            conn.commit()
            logger.info("PostgreSQL tables created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating PostgreSQL tables: {e}")
            raise
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def add_job(self, job_data: Dict[str, Any]) -> Optional[int]:
        """
        Add a new job to the database
        
        Args:
            job_data: Dictionary containing job information
            
        Returns:
            Job ID if successful, None if job already exists
        """
        try:
            now = datetime.now()
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Parse posted_date if it's a string
            posted_date = job_data.get('posted_date')
            if isinstance(posted_date, str):
                try:
                    posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                except:
                    posted_date = None
            
            cursor.execute("""
                INSERT INTO jobs (
                    job_id, source, title, company, location, description, 
                    url, posted_date, salary, discovered_date, last_updated,
                    match_score, match_reasoning, key_alignments, potential_gaps,
                    priority, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                job_data.get('job_id') or job_data.get('external_id'),
                job_data.get('source'),
                job_data.get('title'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('description'),
                job_data.get('url'),
                posted_date,
                job_data.get('salary'),
                now,
                now,
                job_data.get('match_score'),
                job_data.get('match_reasoning') or job_data.get('reasoning'),
                json.dumps(job_data.get('key_alignments', [])),
                json.dumps(job_data.get('potential_gaps', [])),
                job_data.get('priority', 'medium'),
                'new'
            ))
            
            job_id = cursor.fetchone()[0]
            conn.commit()
            return job_id
            
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding job: {e}")
            return None
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def job_exists(self, job_id: str) -> bool:
        """Check if a job already exists in database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM jobs WHERE job_id = %s", (job_id,))
            result = cursor.fetchone() is not None
            return result
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_jobs_by_date(self, date: str, status: str = None) -> List[Dict]:
        """Get jobs discovered on a specific date"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if status:
                cursor.execute("""
                    SELECT * FROM jobs 
                    WHERE DATE(discovered_date) = %s AND status = %s
                    ORDER BY discovered_date DESC
                """, (date, status))
            else:
                cursor.execute("""
                    SELECT * FROM jobs 
                    WHERE DATE(discovered_date) = %s
                    ORDER BY discovered_date DESC
                """, (date,))
            
            jobs = cursor.fetchall()
            return [dict(job) for job in jobs]
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_jobs_by_score(self, min_score: int, max_results: int = 20) -> List[Dict]:
        """Get jobs with match score above threshold"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE match_score >= %s 
                ORDER BY match_score DESC 
                LIMIT %s
            """, (min_score, max_results))
            
            jobs = cursor.fetchall()
            return [dict(job) for job in jobs]
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_jobs_by_priority(self, priority: str) -> List[Dict]:
        """Get jobs by priority level"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE priority = %s 
                ORDER BY discovered_date DESC
            """, (priority,))
            
            jobs = cursor.fetchall()
            return [dict(job) for job in jobs]
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def update_job_status(self, job_id: str, status: str, notes: str = None):
        """Update job status and optionally add notes"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            if notes:
                cursor.execute("""
                    UPDATE jobs 
                    SET status = %s, notes = %s, last_updated = %s
                    WHERE job_id = %s
                """, (status, notes, datetime.now(), job_id))
            else:
                cursor.execute("""
                    UPDATE jobs 
                    SET status = %s, last_updated = %s
                    WHERE job_id = %s
                """, (status, datetime.now(), job_id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating job status: {e}")
            raise
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Total jobs
            cursor.execute("SELECT COUNT(*) as total FROM jobs")
            total_jobs = cursor.fetchone()['total']
            
            # Jobs by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM jobs 
                GROUP BY status
            """)
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Jobs by source
            cursor.execute("""
                SELECT source, COUNT(*) as count 
                FROM jobs 
                GROUP BY source 
                ORDER BY count DESC
            """)
            source_counts = {row['source']: row['count'] for row in cursor.fetchall()}
            
            # Recent jobs
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM jobs 
                WHERE discovered_date >= CURRENT_DATE
            """)
            today_count = cursor.fetchone()['count']
            
            return {
                'total_jobs': total_jobs,
                'by_status': status_counts,
                'by_source': source_counts,
                'discovered_today': today_count
            }
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def add_user_job_match(self, user_id: int, job_id: int, semantic_score: int = None,
                          claude_score: int = None, match_reasoning: str = None,
                          key_alignments: list = None, potential_gaps: list = None,
                          priority: str = 'medium') -> bool:
        """Add or update a user-job match"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()
            
            # Convert lists to comma-separated strings
            key_alignments_str = ', '.join(key_alignments) if key_alignments else ''
            potential_gaps_str = ', '.join(potential_gaps) if potential_gaps else ''
            
            # PostgreSQL upsert
            cursor.execute("""
                INSERT INTO user_job_matches (
                    user_id, job_id, semantic_score, semantic_date,
                    claude_score, claude_date, priority, match_reasoning,
                    key_alignments, potential_gaps, created_date, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, job_id) 
                DO UPDATE SET
                    semantic_score = COALESCE(EXCLUDED.semantic_score, user_job_matches.semantic_score),
                    semantic_date = CASE WHEN EXCLUDED.semantic_score IS NOT NULL 
                                       THEN EXCLUDED.semantic_date 
                                       ELSE user_job_matches.semantic_date END,
                    claude_score = COALESCE(EXCLUDED.claude_score, user_job_matches.claude_score),
                    claude_date = CASE WHEN EXCLUDED.claude_score IS NOT NULL 
                                     THEN EXCLUDED.claude_date 
                                     ELSE user_job_matches.claude_date END,
                    priority = EXCLUDED.priority,
                    match_reasoning = COALESCE(EXCLUDED.match_reasoning, user_job_matches.match_reasoning),
                    key_alignments = COALESCE(EXCLUDED.key_alignments, user_job_matches.key_alignments),
                    potential_gaps = COALESCE(EXCLUDED.potential_gaps, user_job_matches.potential_gaps),
                    last_updated = EXCLUDED.last_updated
            """, (
                user_id, job_id, semantic_score, now if semantic_score else None,
                claude_score, now if claude_score else None, priority, match_reasoning,
                key_alignments_str, potential_gaps_str, now, now
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding user job match: {e}")
            return False
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_user_job_matches(self, user_id: int, min_semantic_score: int = None,
                            min_claude_score: int = None, limit: int = 200,
                            status: str = None) -> List[Dict]:
        """Get job matches for a user"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT ujm.*, j.title, j.company, j.location, j.url, j.description,
                       j.salary, j.source, j.posted_date
                FROM user_job_matches ujm
                JOIN jobs j ON ujm.job_id = j.id
                WHERE ujm.user_id = %s
            """
            params = [user_id]
            
            if min_semantic_score is not None:
                query += " AND ujm.semantic_score >= %s"
                params.append(min_semantic_score)
            
            if min_claude_score is not None:
                query += " AND ujm.claude_score >= %s"
                params.append(min_claude_score)
            
            if status:
                query += " AND ujm.status = %s"
                params.append(status)
            
            query += " ORDER BY COALESCE(ujm.claude_score, ujm.semantic_score) DESC, ujm.last_updated DESC"
            query += " LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            matches = cursor.fetchall()
            return [dict(match) for match in matches]
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def close(self):
        """Close all connections in the pool"""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed")
