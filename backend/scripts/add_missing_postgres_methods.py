#!/usr/bin/env python3
"""
Add all missing methods to PostgreSQL database classes
Run this once to ensure full compatibility with SQLite versions
"""

# This file contains the method implementations to add to postgres_operations.py and postgres_cv_operations.py
# Copy and paste the methods into the appropriate files

POSTGRES_DATABASE_METHODS = '''
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
            print(f"Error permanently deleting job: {e}")
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
            print(f"Error adding search record: {e}")
    
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
            print(f"Error adding feedback: {e}")
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
    
    def get_shortlisted_jobs(self, user_email: str = 'default@localhost') -> List[Dict]:
        """Get jobs marked as shortlisted by user"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE status = 'shortlisted'
                ORDER BY match_score DESC, discovered_date DESC
            """)
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
'''

POSTGRES_CV_MANAGER_METHODS = '''
    def add_user(self, email: str, password: str, name: str = None) -> Optional[int]:
        """Alias for register_user for compatibility"""
        return self.register_user(email, password, name)
    
    def update_user(self, user_id: int, **kwargs):
        """Update user fields"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build dynamic UPDATE query
            fields = []
            values = []
            for key, value in kwargs.items():
                if key == 'preferences':
                    fields.append(f"{key} = %s")
                    values.append(json.dumps(value) if isinstance(value, dict) else value)
                else:
                    fields.append(f"{key} = %s")
                    values.append(value)
            
            if not fields:
                return
            
            fields.append("last_updated = %s")
            values.append(datetime.now())
            values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s"
            cursor.execute(query, values)
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating user: {e}")
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s, last_updated = %s
                WHERE id = %s
            """, (password_hash, datetime.now(), user_id))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            return True
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating password: {e}")
            return False
    
    def update_filter_run_time(self, user_id: int):
        """Update the last filter run timestamp"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            cursor.execute("""
                UPDATE users 
                SET last_filter_run = %s, last_updated = %s
                WHERE id = %s
            """, (now, now, user_id))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating filter run time: {e}")
    
    def update_preferences_time(self, user_id: int):
        """Update the preferences_updated timestamp"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            cursor.execute("""
                UPDATE users 
                SET preferences_updated = %s, last_updated = %s
                WHERE id = %s
            """, (now, now, user_id))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating preferences time: {e}")
    
    def get_all_active_users(self) -> List[Dict]:
        """Get all active users"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM users WHERE is_active = TRUE")
            users = [dict(row) for row in cursor.fetchall()]
            
            cursor.close()
            self._return_connection(conn)
            
            # Parse JSON preferences
            for user in users:
                if user.get('preferences'):
                    try:
                        user['preferences'] = json.loads(user['preferences']) if isinstance(user['preferences'], str) else user['preferences']
                    except:
                        user['preferences'] = {}
            
            return users
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting active users: {e}")
            return []
    
    def archive_cv(self, cv_id: int):
        """Archive a CV (soft delete by setting status='archived')"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE cvs 
                SET status = 'archived'
                WHERE id = %s
            """, (cv_id,))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error archiving CV: {e}")
    
    def update_cv_status(self, cv_id: int, status: str):
        """Update CV status"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE cvs 
                SET status = %s
                WHERE id = %s
            """, (status, cv_id))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating CV status: {e}")
    
    def update_cv_profile(self, profile_id: int, profile_data: Dict):
        """Update CV profile data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            cursor.execute("""
                UPDATE cv_profiles 
                SET technical_skills = %s, soft_skills = %s, languages = %s,
                    education = %s, work_history = %s, achievements = %s,
                    total_years_experience = %s, expertise_summary = %s, career_level = %s,
                    preferred_roles = %s, industries = %s, last_updated = %s
                WHERE id = %s
            """, (
                json.dumps(profile_data.get('technical_skills', [])),
                json.dumps(profile_data.get('soft_skills', [])),
                json.dumps(profile_data.get('languages', [])),
                json.dumps(profile_data.get('education', [])),
                json.dumps(profile_data.get('work_experience', profile_data.get('work_history', []))),
                json.dumps(profile_data.get('career_highlights', profile_data.get('achievements', []))),
                profile_data.get('total_years_experience', 0),
                profile_data.get('expertise_summary'),
                profile_data.get('career_level'),
                json.dumps(profile_data.get('preferred_roles', [])),
                json.dumps(profile_data.get('industries', [])),
                now,
                profile_id
            ))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating CV profile: {e}")
    
    def get_cv_statistics(self, user_id: int) -> Dict:
        """Get CV statistics for a user - alias for get_user_statistics"""
        return self.get_user_statistics(user_id)
    
    def close(self):
        """Close method for compatibility - connection pool managed by PostgresDatabase"""
        pass
'''

print("=" * 80)
print("ADD THESE METHODS TO postgres_operations.py")
print("=" * 80)
print(POSTGRES_DATABASE_METHODS)
print("\n\n")
print("=" * 80)
print("ADD THESE METHODS TO postgres_cv_operations.py")
print("=" * 80)
print(POSTGRES_CV_MANAGER_METHODS)
