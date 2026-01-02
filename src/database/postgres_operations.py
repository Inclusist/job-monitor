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
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    name TEXT,
                    user_role TEXT,
                    location TEXT,
                    created_date TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    preferences TEXT,
                    last_filter_run TIMESTAMP,
                    preferences_updated TIMESTAMP
                )
            """)
            
            # CVs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cvs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    file_hash TEXT,
                    uploaded_date TIMESTAMP NOT NULL,
                    is_primary INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # CV Profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cv_profiles (
                    id SERIAL PRIMARY KEY,
                    cv_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    technical_skills TEXT,
                    soft_skills TEXT,
                    languages TEXT,
                    education TEXT,
                    work_history TEXT,
                    achievements TEXT,
                    total_years_experience REAL,
                    expertise_summary TEXT,
                    career_level TEXT,
                    preferred_roles TEXT,
                    industries TEXT,
                    raw_analysis TEXT,
                    created_date TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    FOREIGN KEY (cv_id) REFERENCES cvs(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                    CONSTRAINT unique_user_job UNIQUE(user_id, job_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                    priority, status,
                    ai_employment_type, ai_work_arrangement, ai_seniority, ai_industry
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                'new',
                job_data.get('ai_employment_type'),
                job_data.get('ai_work_arrangement'),
                job_data.get('ai_seniority'),
                job_data.get('ai_industry')
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
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get a single job by its database ID"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            return dict(job) if job else None
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

    def search_jobs_with_filters(
        self,
        location: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        employment_type: Optional[str] = None,
        seniority: Optional[str] = None,
        industry: Optional[str] = None,
        min_score: Optional[int] = None,
        status: Optional[str] = 'new',
        exclude_location: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search jobs with AI field filters and support for complex queries

        Args:
            location: Filter by location (supports LIKE pattern, e.g., '%Berlin%')
            work_arrangement: Filter by AI work arrangement (remote, hybrid, onsite)
            employment_type: Filter by AI employment type (full-time, part-time, contract)
            seniority: Filter by AI seniority level (entry, mid, senior, lead)
            industry: Filter by AI industry
            min_score: Minimum match score
            status: Job status filter (default: 'new')
            exclude_location: If True with work_arrangement, excludes jobs matching location
            limit: Maximum results to return

        Returns:
            List of job dictionaries matching the filters

        Example usage:
            # Jobs in Berlin OR (Hybrid AND NOT in Berlin)
            berlin_jobs = db.search_jobs_with_filters(location='Berlin')
            hybrid_not_berlin = db.search_jobs_with_filters(
                work_arrangement='Hybrid',
                location='Berlin',
                exclude_location=True
            )
            all_jobs = berlin_jobs + hybrid_not_berlin
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build dynamic WHERE clause
            where_conditions = []
            params = []

            # Status filter
            if status:
                where_conditions.append("status = %s")
                params.append(status)

            # Location filter
            if location:
                if exclude_location:
                    # Exclude this location (for complex queries)
                    where_conditions.append("(location NOT ILIKE %s OR location IS NULL)")
                    params.append(f'%{location}%')
                else:
                    # Include this location
                    where_conditions.append("location ILIKE %s")
                    params.append(f'%{location}%')

            # AI field filters
            if work_arrangement:
                where_conditions.append("ai_work_arrangement ILIKE %s")
                params.append(f'%{work_arrangement}%')

            if employment_type:
                where_conditions.append("ai_employment_type ILIKE %s")
                params.append(f'%{employment_type}%')

            if seniority:
                where_conditions.append("ai_seniority ILIKE %s")
                params.append(f'%{seniority}%')

            if industry:
                where_conditions.append("ai_industry ILIKE %s")
                params.append(f'%{industry}%')

            # Score filter
            if min_score is not None:
                where_conditions.append("match_score >= %s")
                params.append(min_score)

            # Build final query
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            query = f"""
                SELECT * FROM jobs
                WHERE {where_clause}
                ORDER BY match_score DESC, discovered_date DESC
                LIMIT %s
            """
            params.append(limit)

            cursor.execute(query, params)
            jobs = cursor.fetchall()
            return [dict(job) for job in jobs]

        finally:
            cursor.close()
            self._return_connection(conn)

    def search_jobs_with_or_filters(
        self,
        filter_groups: List[Dict[str, Any]],
        status: Optional[str] = 'new',
        limit: int = 100
    ) -> List[Dict]:
        """
        Search jobs with OR logic between filter groups

        Args:
            filter_groups: List of filter dictionaries, each representing a condition group
                          Results matching ANY group will be returned
            status: Job status filter (default: 'new')
            limit: Maximum results to return

        Returns:
            List of unique job dictionaries matching any filter group

        Example usage:
            # Jobs in Berlin OR (Hybrid AND NOT in Berlin)
            filter_groups = [
                {'location': 'Berlin'},  # Jobs in Berlin
                {'work_arrangement': 'Hybrid', 'location': 'Berlin', 'exclude_location': True}  # Hybrid jobs not in Berlin
            ]
            jobs = db.search_jobs_with_or_filters(filter_groups)
        """
        all_jobs = []
        seen_job_ids = set()

        for filters in filter_groups:
            # Extract exclude_location flag if present
            exclude_location = filters.pop('exclude_location', False)

            # Call search_jobs_with_filters for each group
            jobs = self.search_jobs_with_filters(
                location=filters.get('location'),
                work_arrangement=filters.get('work_arrangement'),
                employment_type=filters.get('employment_type'),
                seniority=filters.get('seniority'),
                industry=filters.get('industry'),
                min_score=filters.get('min_score'),
                status=status,
                exclude_location=exclude_location,
                limit=limit
            )

            # Add unique jobs only
            for job in jobs:
                if job['id'] not in seen_job_ids:
                    seen_job_ids.add(job['id'])
                    all_jobs.append(job)

        # Sort by match score and date
        all_jobs.sort(key=lambda x: (x.get('match_score', 0), x.get('discovered_date', '')), reverse=True)

        return all_jobs[:limit]

    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """
        Get a single job by its database ID
        
        Args:
            job_id: Database ID (primary key) of the job
            
        Returns:
            Job dictionary if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            
            job = cursor.fetchone()
            if job:
                return dict(job)
            return None
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_deleted_job_ids(self) -> set:
        """
        Get set of job_ids that have been deleted/hidden
        Used to prevent re-adding deleted jobs in future searches
        
        Returns:
            Set of job_id strings for deleted jobs
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT job_id FROM jobs WHERE status = 'deleted'")
            deleted_ids = {row[0] for row in cursor.fetchall()}
            return deleted_ids
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
    
    def add_user_job_matches_batch(self, matches: List[Dict]) -> int:
        """
        Add multiple user-job matches in a single batch operation
        
        Args:
            matches: List of dicts with keys: user_id, job_id, semantic_score, 
                     match_reasoning, key_alignments, potential_gaps, priority
        
        Returns:
            Number of matches successfully inserted/updated
        """
        if not matches:
            return 0
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()
            
            # Prepare batch data
            values = []
            for match in matches:
                # Convert lists to comma-separated strings
                key_alignments = match.get('key_alignments', [])
                potential_gaps = match.get('potential_gaps', [])
                key_alignments_str = ', '.join(key_alignments) if key_alignments else ''
                potential_gaps_str = ', '.join(potential_gaps) if potential_gaps else ''
                
                values.append((
                    match['user_id'],
                    match['job_id'],
                    match.get('semantic_score'),
                    now if match.get('semantic_score') else None,
                    match.get('claude_score'),
                    now if match.get('claude_score') else None,
                    match.get('priority', 'medium'),
                    match.get('match_reasoning'),
                    key_alignments_str,
                    potential_gaps_str,
                    now,
                    now
                ))
            
            # Use execute_values for efficient batch insert
            from psycopg2.extras import execute_values
            
            execute_values(
                cursor,
                """
                INSERT INTO user_job_matches (
                    user_id, job_id, semantic_score, semantic_date,
                    claude_score, claude_date, priority, match_reasoning,
                    key_alignments, potential_gaps, created_date, last_updated
                ) VALUES %s
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
                """,
                values
            )
            
            conn.commit()
            return len(matches)
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding batch user job matches: {e}")
            return 0
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
                SELECT 
                    ujm.*,
                    j.id as job_table_id,
                    j.job_id,
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
            
            query += " ORDER BY COALESCE(ujm.claude_score, ujm.semantic_score) DESC, ujm.claude_date DESC, ujm.semantic_date DESC"
            query += " LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            matches = cursor.fetchall()
            return [dict(match) for match in matches]
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_jobs_discovered_today(self) -> List[Dict]:
        """Get jobs discovered today (excludes deleted jobs)"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE DATE(discovered_date) = CURRENT_DATE AND status != 'deleted'
                ORDER BY COALESCE(match_score, 0) DESC
            """)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_jobs_discovered_before_today(self, limit: int = 50) -> List[Dict]:
        """Get jobs discovered before today (excludes deleted jobs)"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE DATE(discovered_date) < CURRENT_DATE AND status != 'deleted'
                ORDER BY COALESCE(match_score, 0) DESC, discovered_date DESC
                LIMIT %s
            """, (limit,))
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_deleted_jobs(self, limit: int = 50) -> List[Dict]:
        """Get all deleted/hidden jobs"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE status = 'deleted'
                ORDER BY last_updated DESC
                LIMIT %s
            """, (limit,))
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def permanently_delete_job(self, job_id: int) -> bool:
        """Permanently remove a job from the database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM jobs WHERE id = %s', (job_id,))
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            return True
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error permanently deleting job: {e}")
            return False
    
    def add_search_record(self, source: str, search_term: str, location: str, 
                         results_count: int, execution_time: float):
        """Log a search operation"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_history (
                    search_date, source, search_term, location, results_count, execution_time
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(),
                source,
                search_term,
                location,
                results_count,
                execution_time
            ))
            conn.commit()
            cursor.close()
            self._return_connection(conn)
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error adding search record: {e}")
    
    def add_feedback(self, job_id: int, user_email: str, feedback_type: str, 
                     match_score_original: int, match_score_user: Optional[int] = None,
                     feedback_reason: Optional[str] = None) -> bool:
        """Add user feedback on a job match score"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO job_feedback (
                    job_id, user_email, feedback_type, match_score_original,
                    match_score_user, feedback_reason, created_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                job_id, user_email, feedback_type, match_score_original,
                match_score_user, feedback_reason, datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            return True
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error adding feedback: {e}")
            return False
    
    def get_user_feedback(self, user_email: str, limit: int = 50) -> List[Dict]:
        """Get user's feedback history"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    f.id, f.job_id, f.feedback_type, f.match_score_original,
                    f.match_score_user, f.feedback_reason, f.created_date,
                    j.title, j.company, j.location, j.description,
                    j.key_alignments, j.potential_gaps
                FROM job_feedback f
                JOIN jobs j ON f.job_id = j.id
                WHERE f.user_email = %s
                ORDER BY f.created_date DESC
                LIMIT %s
            """, (user_email, limit))
            
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def update_user_job_status(self, user_id: int, job_id: int, status: str):
        """
        Update user-specific job status in user_job_matches table

        Args:
            user_id: User ID
            job_id: Job ID (database primary key)
            status: New status ('shortlisted', 'deleted', 'viewed', 'applying', 'applied')
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Check if user_job_match exists
            cursor.execute("""
                SELECT id FROM user_job_matches
                WHERE user_id = %s AND job_id = %s
            """, (user_id, job_id))

            match_row = cursor.fetchone()

            if match_row:
                # Update existing record
                cursor.execute("""
                    UPDATE user_job_matches
                    SET status = %s, last_updated = NOW()
                    WHERE user_id = %s AND job_id = %s
                """, (status, user_id, job_id))
            else:
                # Create new record
                cursor.execute("""
                    INSERT INTO user_job_matches
                    (user_id, job_id, status, created_date, last_updated)
                    VALUES (%s, %s, %s, NOW(), NOW())
                """, (user_id, job_id, status))

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating user job status: {e}")
            raise
        finally:
            cursor.close()
            self._return_connection(conn)

    def get_shortlisted_jobs(self, user_email: str = 'default@localhost') -> List[Dict]:
        """Get jobs marked as shortlisted by specific user"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get user_id from email
            cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
            user_row = cursor.fetchone()
            if not user_row:
                return []
            user_id = user_row['id']

            # Query jobs with user-specific status
            cursor.execute("""
                SELECT j.*,
                       ujm.status as user_status,
                       ujm.claude_score,
                       ujm.match_reasoning,
                       ujm.key_alignments,
                       ujm.potential_gaps,
                       COALESCE(ujm.claude_score, ujm.semantic_score, j.match_score) as effective_score
                FROM jobs j
                INNER JOIN user_job_matches ujm ON j.id = ujm.job_id
                WHERE ujm.user_id = %s
                AND ujm.status = 'shortlisted'
                ORDER BY effective_score DESC NULLS LAST,
                         j.discovered_date DESC
            """, (user_id,))

            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def get_unfiltered_jobs_for_user(self, user_id: int) -> List[Dict]:
        """Get jobs that haven't been matched/filtered for this user yet"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT j.* FROM jobs j
                LEFT JOIN user_job_matches ujm ON j.id = ujm.job_id AND ujm.user_id = %s
                WHERE ujm.id IS NULL AND j.status != 'deleted'
                ORDER BY j.discovered_date DESC
            """, (user_id,))
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def count_new_jobs_since(self, user_id: int, since_date: str) -> int:
        """Count new jobs discovered since a specific date"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM jobs
                WHERE discovered_date >= %s AND status != 'deleted'
            """, (since_date,))
            count = cursor.fetchone()[0]
            return count
        finally:
            cursor.close()
            self._return_connection(conn)

    def get_unique_query_combinations(self) -> List[Dict]:
        """
        Get DISTINCT query combinations across all users

        This is the KEY method for quota efficiency!
        Returns unique combinations of (title_keyword, location, AI filters)
        regardless of which user created them.

        Example:
            User 1: "data scientist" in "Berlin"
            User 2: "data scientist" in "Berlin"  <- Duplicate!
            Returns only 1 combination

        Returns:
            List of unique query combination dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get distinct combinations - this is where deduplication happens!
            cursor.execute("""
                SELECT DISTINCT
                    title_keyword,
                    location,
                    ai_work_arrangement,
                    ai_employment_type,
                    ai_seniority,
                    ai_industry,
                    MAX(priority) as max_priority
                FROM user_search_queries
                WHERE is_active = TRUE
                GROUP BY title_keyword, location, ai_work_arrangement,
                         ai_employment_type, ai_seniority, ai_industry
                ORDER BY max_priority DESC
            """)

            combinations = cursor.fetchall()
            cursor.close()
            self._return_connection(conn)

            logger.info(f"Found {len(combinations)} unique query combinations across all users")
            return [dict(c) for c in combinations]

        except Exception as e:
            if 'conn' in locals():
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error getting unique query combinations: {e}")
            return []

    def get_all_active_queries(self) -> List[Dict]:
        """
        Get all active search queries across all users (NOT deduplicated)

        Use get_unique_query_combinations() for job loading to save quota!

        Returns:
            List of all query rows with user info
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT
                    q.*,
                    u.email as user_email,
                    u.name as user_name
                FROM user_search_queries q
                JOIN users u ON q.user_id = u.id
                WHERE q.is_active = TRUE
                ORDER BY q.priority DESC, q.user_id ASC, q.id ASC
            """)

            queries = cursor.fetchall()
            cursor.close()
            self._return_connection(conn)

            return [dict(q) for q in queries]

        except Exception as e:
            if 'conn' in locals():
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error getting all active queries: {e}")
            return []

    def close(self):
        """Close all connections in the pool"""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed")
