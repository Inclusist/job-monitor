"""
PostgreSQL CV and User operations - compatible with CVManager
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional
import json
import bcrypt
import logging

logger = logging.getLogger(__name__)


class PostgresCVManager:
    """PostgreSQL-based CV and User operations"""
    
    def __init__(self, connection_pool):
        """
        Initialize with existing PostgreSQL connection pool
        
        Args:
            connection_pool: psycopg2 connection pool from PostgresDatabase
        """
        self.connection_pool = connection_pool
        self._ensure_tables()
    
    def _get_connection(self):
        """Get a connection from the pool, validating it's still alive"""
        conn = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.connection_pool.getconn()
                # Determine if the connection is actually alive
                if conn.closed == 0:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    return conn
                else:
                    logger.warning(f"Connection from pool is closed (attempt {attempt+1}/{max_retries})")
                    self.connection_pool.putconn(conn, close=True)
                    conn = None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                logger.warning(f"PostgreSQL connection error: {e} (attempt {attempt+1}/{max_retries})")
                if conn:
                    try:
                        self.connection_pool.putconn(conn, close=True)
                    except:
                        pass
                    conn = None
                
                # If it's the last attempt, re-raise
                if attempt == max_retries - 1:
                    logger.error("Failed to get a valid PostgreSQL connection after multiple attempts")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error getting connection: {e}")
                if conn:
                    self.connection_pool.putconn(conn)
                raise
        
        raise Exception("Could not acquire a valid database connection")

    def _return_connection(self, conn):
        """Return connection to pool"""
        if conn:
            try:
                self.connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Error returning connection to pool: {e}")
    
    def _ensure_tables(self):
        """Ensure user/CV tables exist (already created by PostgresDatabase)"""
        pass
    
    def register_user(self, email: str, password: str, name: str = None) -> Optional[int]:
        """Register a new user"""
        try:
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, created_date, last_updated, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (email, password_hash, name, now, now, 1))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            cursor.close()
            self._return_connection(conn)
            
            logger.info(f"User registered: {email} (ID: {user_id})")
            return user_id
            
        except psycopg2.IntegrityError:
            conn.rollback()
            cursor.close()
            self._return_connection(conn)
            logger.warning(f"User already exists: {email}")
            return None
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error registering user: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user dict (compatible with SQLite CVManager)"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT id, password_hash FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
            user = cursor.fetchone()
            
            if not user:
                cursor.close()
                self._return_connection(conn)
                return None
            
            # Check password
            password_match = bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8'))
            
            cursor.close()
            self._return_connection(conn)
            
            if password_match:
                # Return full user dict like SQLite version does
                return self.get_user_by_id(user['id'])
            
            return None
            
        except Exception as e:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    self._return_connection(conn)
                except:
                    pass
            logger.error(f"Error authenticating user: {e}")
            return None
    
    def get_or_create_oauth_user(self, email: str, name: str = None, provider: str = 'google', avatar_url: str = None) -> Optional[Dict]:
        """
        Get or create user from OAuth provider (Google, LinkedIn, etc.)
        
        Args:
            email: User's email address from OAuth provider
            name: User's name from OAuth provider
            provider: OAuth provider name ('google', 'linkedin')
            avatar_url: Profile picture URL from OAuth provider
            
        Returns:
            User dict with is_new_user flag, or None on error
        """
        conn = None
        cursor = None
        try:
            # Check if user already exists
            existing_user = self.get_user_by_email(email)
            
            if existing_user:
                # Update provider and avatar if not set
                conn = self._get_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get preferences (already parsed as dict by get_user_by_email)
                preferences = existing_user.get('preferences') or {}
                needs_update = False
                
                # Update name if not set
                update_name = name and not existing_user.get('name')
                
                # Store OAuth provider info in preferences
                if 'oauth_provider' not in preferences:
                    preferences['oauth_provider'] = provider
                    needs_update = True
                if avatar_url and 'avatar_url' not in preferences:
                    preferences['avatar_url'] = avatar_url
                    needs_update = True
                
                if update_name or needs_update:
                    update_parts = []
                    params = []
                    
                    if update_name:
                        update_parts.append("name = %s")
                        params.append(name)
                    
                    if needs_update:
                        update_parts.append("preferences = %s")
                        params.append(json.dumps(preferences))
                    
                    update_parts.append("last_updated = %s")
                    params.append(datetime.now())  # Use datetime object, not ISO string
                    
                    params.append(existing_user['id'])
                    
                    cursor.execute(f"""
                        UPDATE users 
                        SET {', '.join(update_parts)}
                        WHERE id = %s
                    """, params)
                    
                    conn.commit()
                
                cursor.close()
                self._return_connection(conn)
                
                # Reload user
                user = self.get_user_by_email(email)
                user['is_new_user'] = False
                user['provider'] = preferences.get('oauth_provider', 'email')
                user['avatar_url'] = preferences.get('avatar_url')
                return user
            
            # Create new user with OAuth
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            now = datetime.now()  # Use datetime object, not ISO string for PostgreSQL
            
            # Store OAuth info in preferences
            preferences = {
                'oauth_provider': provider,
                'avatar_url': avatar_url
            }
            
            cursor.execute("""
                INSERT INTO users (
                    email, password_hash, name, created_date, last_updated, preferences
                ) VALUES (%s, NULL, %s, %s, %s, %s)
                RETURNING id
            """, (email.lower(), name, now, now, json.dumps(preferences)))
            
            result = cursor.fetchone()
            user_id = result['id']
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
            # Return new user with flag
            user = self.get_user_by_id(user_id)
            user['is_new_user'] = True
            user['provider'] = provider
            user['avatar_url'] = avatar_url
            return user
            
        except Exception as e:
            import traceback
            logger.error(f"Error creating OAuth user: {e}")
            logger.error(traceback.format_exc())
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.rollback()
                    self._return_connection(conn)
                except:
                    pass
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            if user:
                # Parse JSON preferences if present
                user_dict = dict(user)
                if user_dict.get('preferences'):
                    try:
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                    except:
                        user_dict['preferences'] = {}
                else:
                    user_dict['preferences'] = {}
                return user_dict
            
            return None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID (alias for get_user_by_id)"""
        return self.get_user_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email (case-insensitive)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
            user = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            if user:
                # Parse JSON preferences if present
                user_dict = dict(user)
                if user_dict.get('preferences'):
                    try:
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                    except:
                        user_dict['preferences'] = {}
                else:
                    user_dict['preferences'] = {}
                return user_dict
            
            return None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Update user preferences"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert preferences dict to JSON string
            preferences_json = json.dumps(preferences)
            now = datetime.now()
            
            cursor.execute("""
                UPDATE users 
                SET preferences = %s, preferences_updated = %s, last_updated = %s
                WHERE id = %s
            """, (preferences_json, now, now, user_id))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
            logger.info(f"Updated preferences for user {user_id}")
            return True
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating preferences: {e}")
            return False
    
    def should_refilter(self, user_id: int) -> tuple:
        """
        Check if user needs re-filtering based on last run, preferences, and new jobs
        
        Returns:
            (should_refilter, reason)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT last_filter_run, preferences_updated
                FROM users WHERE id = %s
            """, (user_id,))
            row = cursor.fetchone()
            
            if not row:
                cursor.close()
                self._return_connection(conn)
                return (True, "User not found")
            
            last_filter = row['last_filter_run']
            prefs_updated = row['preferences_updated']
            
            if not last_filter:
                cursor.close()
                self._return_connection(conn)
                return (True, "Never filtered")
            
            if prefs_updated and prefs_updated > last_filter:
                cursor.close()
                self._return_connection(conn)
                return (True, "Preferences changed since last filter")
            
            # Check if there are new jobs since last filter run
            cursor.execute("""
                SELECT COUNT(*) as new_jobs
                FROM jobs
                WHERE created_at > %s
            """, (last_filter,))
            new_jobs_count = cursor.fetchone()['new_jobs']
            
            cursor.close()
            self._return_connection(conn)
            
            if new_jobs_count > 0:
                return (True, f"{new_jobs_count} new jobs since last run")
            
            return (False, "Up to date")
            
        except Exception as e:
            logger.error(f"Error checking refilter status: {e}")
            return (True, "Error checking status")
    
    def save_cv(self, user_id: int, file_name: str, file_path: str, file_type: str, 
                file_size: int = None, file_hash: str = None) -> Optional[int]:
        """Save CV file information"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            cursor.execute("""
                INSERT INTO cvs (
                    user_id, file_name, file_path, file_type, file_size, file_hash,
                    uploaded_date, is_primary, version, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, file_name, file_path, file_type, file_size, file_hash,
                  now, 1, 1, 'active'))
            
            cv_id = cursor.fetchone()[0]
            conn.commit()
            
            cursor.close()
            self._return_connection(conn)
            
            logger.info(f"Saved CV for user {user_id}: {file_name} (CV ID: {cv_id})")
            return cv_id
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error saving CV: {e}")
            return None
    
    def save_cv_profile(self, cv_id: int, user_id: int, profile_data: Dict) -> Optional[int]:
        """Save CV profile analysis"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            cursor.execute("""
                INSERT INTO cv_profiles (
                    cv_id, user_id, technical_skills, soft_skills, competencies, languages,
                    education, work_history, achievements, expertise_summary,
                    career_level, preferred_roles, industries, raw_analysis,
                    created_date, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                cv_id, user_id,
                json.dumps(profile_data.get('technical_skills', [])),
                json.dumps(profile_data.get('soft_skills', [])),
                json.dumps(profile_data.get('competencies', [])),
                json.dumps(profile_data.get('languages', [])),
                json.dumps(profile_data.get('education', [])),
                json.dumps(profile_data.get('work_history', []) or profile_data.get('work_experience', [])),
                json.dumps(profile_data.get('achievements', []) or profile_data.get('career_highlights', [])),
                profile_data.get('expertise_summary', ''),
                profile_data.get('career_level', ''),
                json.dumps(profile_data.get('preferred_roles', [])),
                json.dumps(profile_data.get('industries', [])),
                json.dumps(profile_data.get('raw_analysis', {})),
                now, now
            ))
            
            profile_id = cursor.fetchone()[0]
            conn.commit()
            
            cursor.close()
            self._return_connection(conn)
            
            logger.info(f"Saved CV profile for user {user_id}, CV {cv_id} (Profile ID: {profile_id})")
            return profile_id
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error saving CV profile: {e}")
            return None
    
    def get_user_cv_profile(self, user_id: int) -> Optional[Dict]:
        """Get latest CV profile for user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM cv_profiles 
                WHERE user_id = %s 
                ORDER BY created_date DESC 
                LIMIT 1
            """, (user_id,))
            
            profile = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            if profile:
                # Parse JSON fields
                profile_dict = dict(profile)
                json_fields = ['technical_skills', 'soft_skills', 'languages', 'education',
                              'work_history', 'achievements', 'preferred_roles', 'industries', 'raw_analysis']
                for field in json_fields:
                    if profile_dict.get(field):
                        try:
                            profile_dict[field] = json.loads(profile_dict[field])
                        except:
                            profile_dict[field] = []
                
                # Map PostgreSQL field names to template-expected names
                if 'work_history' in profile_dict:
                    profile_dict['work_experience'] = profile_dict['work_history']
                if 'achievements' in profile_dict:
                    profile_dict['career_highlights'] = profile_dict['achievements']
                
                return profile_dict
            
            return None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting CV profile: {e}")
            return None
    
    def get_or_create_user(self, email: str, name: str = None, **kwargs) -> Dict:
        """Get existing user or create new one (without password)"""
        user = self.get_user_by_email(email)
        if user:
            return user
        
        # Create user without password (for CV uploads without registration)
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            now = datetime.now()
            cursor.execute("""
                INSERT INTO users (email, name, created_date, last_updated, is_active)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (email, name, now, now, 1))
            
            user_id = cursor.fetchone()['id']
            conn.commit()
            
            cursor.close()
            self._return_connection(conn)
            
            return self.get_user_by_id(user_id)
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """Get user statistics"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Count CVs
            cursor.execute("SELECT COUNT(*) FROM cvs WHERE user_id = %s", (user_id,))
            cv_count = cursor.fetchone()[0]
            
            # Count profiles
            cursor.execute("SELECT COUNT(*) FROM cv_profiles WHERE user_id = %s", (user_id,))
            profile_count = cursor.fetchone()[0]
            
            cursor.close()
            self._return_connection(conn)
            
            return {
                'cv_count': cv_count,
                'profile_count': profile_count
            }
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting user statistics: {e}")
            return {'cv_count': 0, 'profile_count': 0}
    
    def get_user_cvs(self, user_id: int, status: str = 'active') -> list:
        """Get all CVs for user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM cvs 
                WHERE user_id = %s AND status = %s
                ORDER BY uploaded_date DESC
            """, (user_id, status))
            
            cvs = [dict(row) for row in cursor.fetchall()]
            
            cursor.close()
            self._return_connection(conn)
            
            return cvs
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting user CVs: {e}")
            return []
    
    def get_primary_cv(self, user_id: int) -> Optional[Dict]:
        """Get primary CV for user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM cvs 
                WHERE user_id = %s AND is_primary = 1 AND status = 'active'
                ORDER BY uploaded_date DESC
                LIMIT 1
            """, (user_id,))
            
            cv = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            return dict(cv) if cv else None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting primary CV: {e}")
            return None

    def get_primary_profile(self, user_id: int) -> Optional[Dict]:
        """
        Get the specific profile associated with the user's Primary CV.
        This effectively acts as the 'Primary Profile'.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT p.* 
                FROM cv_profiles p
                JOIN cvs c ON p.cv_id = c.id
                WHERE c.user_id = %s AND c.is_primary = 1
                ORDER BY p.created_date DESC
                LIMIT 1
            """, (user_id,))
            
            profile = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            if profile:
                # Reuse parsing logic via get_cv_profile if possible, but for now duplicate parsing:
                profile_dict = dict(profile)
                json_fields = ['technical_skills', 'soft_skills', 'competencies', 'languages', 'education',
                              'work_history', 'achievements', 'preferred_roles', 'industries', 'raw_analysis', 'projects']
                for field in json_fields:
                    if profile_dict.get(field):
                        try:
                            profile_dict[field] = json.loads(profile_dict[field])
                        except:
                            profile_dict[field] = []
                
                # Use raw_analysis competencies as fallback if column is empty (legacy support)
                if not profile_dict.get('competencies'):
                    raw = profile_dict.get('raw_analysis', {})
                    if isinstance(raw, dict):
                         profile_dict['competencies'] = raw.get('competencies', [])

                return profile_dict
            
            return None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting primary profile: {e}")
            return None
    
    def get_cv_profile(self, cv_id: int, include_full_text: bool = False) -> Optional[Dict]:
        """Get CV profile by CV ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM cv_profiles 
                WHERE cv_id = %s
                ORDER BY created_date DESC
                LIMIT 1
            """, (cv_id,))
            
            profile = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            if profile:
                profile_dict = dict(profile)
                json_fields = ['technical_skills', 'soft_skills', 'competencies', 'languages', 'education',
                              'work_history', 'achievements', 'preferred_roles', 'industries', 'raw_analysis', 'projects']
                for field in json_fields:
                    val = profile_dict.get(field)
                    if val:
                        if isinstance(val, str):
                            try:
                                profile_dict[field] = json.loads(val)
                            except:
                                profile_dict[field] = []
                        # already list/dict (JSONB or prev parsed) - do nothing

                # Use raw_analysis competencies as fallback
                if not profile_dict.get('competencies'):
                    raw = profile_dict.get('raw_analysis', {})
                    if isinstance(raw, dict):
                         profile_dict['competencies'] = raw.get('competencies', [])
                
                # Map PostgreSQL field names to template-expected names
                if 'work_history' in profile_dict:
                    profile_dict['work_experience'] = profile_dict['work_history']
                if 'achievements' in profile_dict:
                    profile_dict['career_highlights'] = profile_dict['achievements']
                
                return profile_dict
            
            return None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting CV profile: {e}")
            return None
    
    def get_cv(self, cv_id: int) -> Optional[Dict]:
        """Get CV by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM cvs WHERE id = %s", (cv_id,))
            cv = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            return dict(cv) if cv else None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting CV: {e}")
            return None
    
    def delete_cv(self, cv_id: int):
        """Delete CV"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("UPDATE cvs SET status = 'deleted' WHERE id = %s", (cv_id,))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
            logger.info(f"CV {cv_id} deleted")
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error deleting CV: {e}")
    
    def set_primary_cv(self, user_id: int, cv_id: int):
        """Set primary CV for user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Unset all primary flags for user
            cursor.execute("UPDATE cvs SET is_primary = 0 WHERE user_id = %s", (user_id,))
            
            # Set new primary
            cursor.execute("UPDATE cvs SET is_primary = 1 WHERE id = %s", (cv_id,))
            
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            
            logger.info(f"Set CV {cv_id} as primary for user {user_id}")
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error setting primary CV: {e}")
    
    def get_profile_by_user(self, user_id: int) -> Optional[Dict]:
        """Get latest CV profile for user (alias for get_user_cv_profile)"""
        return self.get_user_cv_profile(user_id)
    
    def get_user_search_preferences(self, user_id: int) -> Dict:
        """
        Get user's search preferences (keywords, locations)
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with 'keywords' and 'locations' lists
        """
        user = self.get_user_by_id(user_id)
        if user and user.get('preferences'):
            prefs = user['preferences']
            return {
                'keywords': prefs.get('search_keywords', []),
                'locations': prefs.get('search_locations', [])
            }
        return {'keywords': [], 'locations': []}
    
    def update_user_search_preferences(self, user_id: int, keywords: List[str] = None, 
                                      locations: List[str] = None) -> bool:
        """
        Update user's search preferences
        
        Args:
            user_id: User ID
            keywords: List of job search keywords
            locations: List of locations to search
            
        Returns:
            True if successful, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Validate inputs
        if keywords is not None:
            if not isinstance(keywords, list):
                logger.error(f"Keywords must be a list, got {type(keywords)}")
                return False
            if len(keywords) == 0:
                logger.warning("Empty keywords list provided")
            # Remove empty strings and duplicates
            keywords = list(set([k.strip() for k in keywords if k and k.strip()]))
        
        if locations is not None:
            if not isinstance(locations, list):
                logger.error(f"Locations must be a list, got {type(locations)}")
                return False
            if len(locations) == 0:
                logger.warning("Empty locations list provided")
            # Remove empty strings and duplicates
            locations = list(set([l.strip() for l in locations if l and l.strip()]))
        
        preferences = user.get('preferences') or {}
        if keywords is not None:
            preferences['search_keywords'] = keywords
        if locations is not None:
            preferences['search_locations'] = locations
        
        self.update_user_preferences(user_id, preferences)
        return True

    def update_user_location(self, user_id: int, location: str) -> bool:
        """
        Update user's current location

        Args:
            user_id: User ID
            location: User's location (e.g., "Berlin, Germany")

        Returns:
            True if successful, False otherwise
        """
        if not location or not isinstance(location, str):
            logger.warning(f"Invalid location provided: {location}")
            return False

        location = location.strip()
        if not location:
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET location = %s,
                    last_updated = NOW()
                WHERE id = %s
            """, (location, user_id))

            conn.commit()
            self._return_connection(conn)

            logger.info(f"Updated location for user {user_id} to: {location}")
            return True

        except Exception as e:
            logger.error(f"Error updating user location: {e}")
            if conn:
                conn.rollback()
                self._return_connection(conn)
            return False

    def add_cv(self, user_id: int, file_name: str, file_path: str,
               file_type: str, file_size: int, file_hash: str,
               version: int = 1) -> Optional[int]:
        """
        Add a new CV to the database

        Args:
            user_id: User ID
            file_name: Original filename
            file_path: Relative path to stored file
            file_type: pdf, docx, or txt
            file_size: Size in bytes
            file_hash: SHA-256 hash
            version: CV version number

        Returns:
            CV ID if successful, None if duplicate or error
        """
        # Validate inputs
        if not file_name or not file_path:
            logger.error("file_name and file_path are required")
            return None
        
        if file_type not in ['pdf', 'docx', 'txt']:
            logger.error(f"Invalid file_type: {file_type}. Must be pdf, docx, or txt")
            return None
        
        if file_size and file_size > 10 * 1024 * 1024:  # 10MB limit
            logger.error(f"File size {file_size} exceeds 10MB limit")
            return None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check for duplicate by file_hash (only active CVs)
            if file_hash:
                cursor.execute("""
                    SELECT id, status FROM cvs 
                    WHERE user_id = %s AND file_hash = %s
                """, (user_id, file_hash))
                existing = cursor.fetchone()
                if existing:
                    existing_id, existing_status = existing
                    logger.info(f"Found existing CV {existing_id} with status '{existing_status}' for user {user_id}")
                    
                    # Only block if it's an active CV
                    if existing_status not in ('archived', 'deleted'):
                        cursor.close()
                        self._return_connection(conn)
                        logger.warning(f"Duplicate active CV detected for user {user_id} with hash {file_hash}")
                        return None
                    else:
                        logger.info(f"Existing CV is {existing_status}, allowing re-upload")
            
            now = datetime.now()

            cursor.execute("""
                INSERT INTO cvs (
                    user_id, file_name, file_path, file_type, file_size,
                    file_hash, uploaded_date, version, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')
                RETURNING id
            """, (
                user_id, file_name, file_path, file_type, file_size,
                file_hash, now, version
            ))

            cv_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            return cv_id

        except Exception as e:
            logger.error(f"Error adding CV: {e}")
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.rollback()
                self._return_connection(conn)
            return None

    def add_cv_profile(self, cv_id: int, user_id: int, profile_data: Dict) -> int:
        """
        Add parsed CV profile data

        Args:
            cv_id: CV ID
            user_id: User ID
            profile_data: Parsed profile dictionary

        Returns:
            Profile ID
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.now()

            cursor.execute("""
                INSERT INTO cv_profiles (
                    cv_id, user_id, technical_skills, soft_skills, languages,
                    education, work_history, achievements, total_years_experience,
                    expertise_summary, career_level, preferred_roles, industries,
                    raw_analysis, projects, created_date, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                cv_id,
                user_id,
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
                json.dumps({k: v for k, v in profile_data.items() if k != 'full_text'}),
                json.dumps(profile_data.get('projects', [])),
                now,
                now
            ))

            profile_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            self._return_connection(conn)
            return profile_id

        except Exception as e:
            logger.error(f"Error adding CV profile: {e}")
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.rollback()
                self._return_connection(conn)
            return None
    
    def check_duplicate_hash(self, user_id: int, file_hash: str) -> Optional[Dict]:
        """Check if CV with same hash already exists"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM cvs
                WHERE user_id = %s AND file_hash = %s AND status = 'active'
            """, (user_id, file_hash))
            
            row = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            return dict(row) if row else None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error checking duplicate hash: {e}")
            return None
    
    # Additional compatibility methods
    def add_user(self, email: str, password: str, name: str = None) -> Optional[int]:
        """Alias for register_user for compatibility"""
        return self.register_user(email, password, name)
    
    def update_user(self, user_id: int, **kwargs):
        """Update user fields"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
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
        """Update the last filter run timestamp, shifting current to previous"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now = datetime.now()
            cursor.execute("""
                UPDATE users
                SET previous_filter_run = last_filter_run,
                    last_filter_run = %s,
                    last_updated = %s
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
    
    def update_cv_status(self, cv_id: int, status: str) -> bool:
        """Update CV status
        
        Returns:
            True if successful, False otherwise
        """
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
            return True
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating CV status: {e}")
            return False
    
    def update_cv_profile(self, cv_id: int, profile_data: Dict):
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
                    preferred_roles = %s, industries = %s, raw_analysis = %s, projects = %s, last_updated = %s
                WHERE cv_id = %s
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
                json.dumps({k: v for k, v in profile_data.items()
                           if k not in ('full_text', 'created_date', 'last_updated', 'cv_id', 'user_id', 'id', 'is_primary')}),
                json.dumps(profile_data.get('projects', [])),
                now,
                cv_id
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
            print(f"CRITICAL SQL ERROR in update_cv_profile: {e}")
    
    def get_cv_statistics(self, user_id: int) -> Dict:
        """Get CV statistics for a user - alias for get_user_statistics"""
        return self.get_user_statistics(user_id)

    # ==================== User Search Queries Management ====================

    def add_user_search_queries(
        self,
        user_id: int,
        query_name: str,
        title_keywords: List[str] = None,
        locations: List[str] = None,
        ai_work_arrangement: str = None,
        ai_employment_type: str = None,
        ai_seniority: str = None,
        ai_industry: str = None,
        priority: int = 0
    ) -> int:
        """
        Add personalized search queries for a user (NORMALIZED)

        Creates separate rows for each title+location combination.
        Example: 2 titles × 2 locations = 4 rows

        Args:
            user_id: User ID
            query_name: Name/description (e.g., "Primary Search")
            title_keywords: List of keywords (e.g., ["data scientist", "ML engineer"])
            locations: List of locations (e.g., ["Berlin", "Hamburg"])
            ai_work_arrangement: Work arrangement filter (single value)
            ai_employment_type: Employment type filter
            ai_seniority: Seniority level filter
            ai_industry: Industry filter
            priority: Query priority

        Returns:
            Number of rows inserted
        """
        try:
            # Ensure we have at least one title or location
            if not title_keywords and not locations:
                logger.warning("No title_keywords or locations provided")
                return 0

            # Default to [None] if not provided
            titles = title_keywords or [None]
            locs = locations or [None]

            conn = self._get_connection()
            cursor = conn.cursor()

            inserted_count = 0

            # Create all combinations of title × location
            for title in titles:
                for location in locs:
                    try:
                        cursor.execute("""
                            INSERT INTO user_search_queries (
                                user_id, query_name, title_keyword, location,
                                ai_work_arrangement, ai_employment_type, ai_seniority, ai_industry,
                                priority
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            user_id, query_name, title, location,
                            ai_work_arrangement, ai_employment_type, ai_seniority, ai_industry,
                            priority
                        ))

                        if cursor.rowcount > 0:
                            inserted_count += 1

                    except Exception as e:
                        logger.warning(f"Could not insert query row (title={title}, loc={location}): {e}")
                        continue

            conn.commit()
            cursor.close()
            self._return_connection(conn)

            logger.info(f"Added {inserted_count} search query rows for user {user_id} (query: {query_name})")
            return inserted_count

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error adding user search queries: {e}")
            return 0

    def get_user_search_queries(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """
        Get all search queries for a user

        Args:
            user_id: User ID
            active_only: If True, only return active queries

        Returns:
            List of query dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if active_only:
                cursor.execute("""
                    SELECT * FROM user_search_queries
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY priority DESC, id ASC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT * FROM user_search_queries
                    WHERE user_id = %s
                    ORDER BY priority DESC, id ASC
                """, (user_id,))

            queries = cursor.fetchall()
            cursor.close()
            self._return_connection(conn)

            return [dict(q) for q in queries]

        except Exception as e:
            if 'conn' in locals():
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error getting user search queries: {e}")
            return []

    def deactivate_user_search_queries(self, user_id: int) -> bool:
        """
        Deactivate all search queries for a user

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE user_search_queries
                SET is_active = FALSE
                WHERE user_id = %s
            """, (user_id,))

            rows_affected = cursor.rowcount
            conn.commit()
            cursor.close()
            self._return_connection(conn)

            logger.info(f"Deactivated {rows_affected} search queries for user {user_id}")
            return True

        except Exception as e:
            if 'conn' in locals():
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error deactivating queries for user {user_id}: {e}")
            return False

    def update_user_search_query(
        self,
        query_id: int,
        **kwargs
    ) -> bool:
        """
        Update a search query

        Args:
            query_id: Query ID
            **kwargs: Fields to update (query_name, title_keywords, locations, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build update query dynamically
            allowed_fields = [
                'query_name', 'title_keywords', 'locations',
                'ai_work_arrangement', 'ai_employment_type', 'ai_seniority', 'ai_industry',
                'is_active', 'priority', 'max_results'
            ]

            updates = []
            values = []

            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = %s")
                    values.append(value)

            if not updates:
                return False

            values.append(query_id)

            conn = self._get_connection()
            cursor = conn.cursor()

            query = f"""
                UPDATE user_search_queries
                SET {', '.join(updates)}
                WHERE id = %s
            """

            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            self._return_connection(conn)

            logger.info(f"Updated search query {query_id}")
            return True

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating search query: {e}")
            return False

    def delete_user_search_query(self, query_id: int) -> bool:
        """
        Delete a search query

        Args:
            query_id: Query ID

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM user_search_queries WHERE id = %s", (query_id,))

            conn.commit()
            cursor.close()
            self._return_connection(conn)

            logger.info(f"Deleted search query {query_id}")
            return True

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error deleting search query: {e}")
            return False

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

    def update_query_run_stats(self, query_id: int, job_count: int) -> bool:
        """
        Update query statistics after a run

        Args:
            query_id: Query ID
            job_count: Number of jobs found in this run

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE user_search_queries
                SET last_run_date = NOW(),
                    last_job_count = %s
                WHERE id = %s
            """, (job_count, query_id))

            conn.commit()
            cursor.close()
            self._return_connection(conn)

            return True

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error updating query stats: {e}")
            return False

    # ==================== Backfill Tracking ====================

    def get_unbacked_combinations_for_user(self, user_id: int) -> List[Dict]:
        """
        Get query combinations for a user that haven't been backfilled yet

        Args:
            user_id: User ID

        Returns:
            List of combinations needing backfill
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get user's unique combinations that are NOT in backfill_tracking
            cursor.execute("""
                SELECT DISTINCT
                    usq.title_keyword,
                    usq.location,
                    usq.ai_work_arrangement,
                    usq.ai_employment_type,
                    usq.ai_seniority,
                    usq.ai_industry
                FROM user_search_queries usq
                LEFT JOIN backfill_tracking bt ON (
                    (usq.title_keyword = bt.title_keyword OR (usq.title_keyword IS NULL AND bt.title_keyword IS NULL))
                    AND (usq.location = bt.location OR (usq.location IS NULL AND bt.location IS NULL))
                    AND (usq.ai_work_arrangement = bt.ai_work_arrangement OR (usq.ai_work_arrangement IS NULL AND bt.ai_work_arrangement IS NULL))
                    AND (usq.ai_employment_type = bt.ai_employment_type OR (usq.ai_employment_type IS NULL AND bt.ai_employment_type IS NULL))
                    AND (usq.ai_seniority = bt.ai_seniority OR (usq.ai_seniority IS NULL AND bt.ai_seniority IS NULL))
                    AND (usq.ai_industry = bt.ai_industry OR (usq.ai_industry IS NULL AND bt.ai_industry IS NULL))
                )
                WHERE usq.user_id = %s
                  AND usq.is_active = TRUE
                  AND bt.id IS NULL
            """, (user_id,))

            combinations = cursor.fetchall()
            cursor.close()
            self._return_connection(conn)

            logger.info(f"Found {len(combinations)} unbacked combinations for user {user_id}")
            return [dict(c) for c in combinations]

        except Exception as e:
            if 'conn' in locals():
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error getting unbacked combinations: {e}")
            return []

    def mark_combination_backfilled(
        self,
        title_keyword: str = None,
        location: str = None,
        ai_work_arrangement: str = None,
        ai_employment_type: str = None,
        ai_seniority: str = None,
        ai_industry: str = None,
        jobs_found: int = 0
    ) -> bool:
        """
        Mark a combination as backfilled

        Args:
            title_keyword: Title keyword
            location: Location
            ai_work_arrangement: Work arrangement filter
            ai_employment_type: Employment type filter
            ai_seniority: Seniority filter
            ai_industry: Industry filter
            jobs_found: Number of jobs found

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO backfill_tracking (
                    title_keyword, location, ai_work_arrangement,
                    ai_employment_type, ai_seniority, ai_industry,
                    jobs_found
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                title_keyword, location, ai_work_arrangement,
                ai_employment_type, ai_seniority, ai_industry,
                jobs_found
            ))

            conn.commit()
            cursor.close()
            self._return_connection(conn)

            logger.info(f"Marked as backfilled: {title_keyword} in {location}")
            return True

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error marking combination as backfilled: {e}")
            return False

    def is_combination_backfilled(
        self,
        title_keyword: str = None,
        location: str = None,
        ai_work_arrangement: str = None,
        ai_seniority: str = None
    ) -> bool:
        """
        Check if a combination has been backfilled

        Args:
            title_keyword: Title keyword
            location: Location
            ai_work_arrangement: Work arrangement
            ai_seniority: Seniority

        Returns:
            True if already backfilled
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM backfill_tracking
                    WHERE (title_keyword = %s OR (title_keyword IS NULL AND %s IS NULL))
                      AND (location = %s OR (location IS NULL AND %s IS NULL))
                      AND (ai_work_arrangement = %s OR (ai_work_arrangement IS NULL AND %s IS NULL))
                      AND (ai_seniority = %s OR (ai_seniority IS NULL AND %s IS NULL))
                )
            """, (
                title_keyword, title_keyword,
                location, location,
                ai_work_arrangement, ai_work_arrangement,
                ai_seniority, ai_seniority
            ))

            exists = cursor.fetchone()[0]
            cursor.close()
            self._return_connection(conn)

            return exists

        except Exception as e:
            if 'conn' in locals():
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error checking if combination is backfilled: {e}")
            return False

    # ==================== Job Operations (for backfill support) ====================

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
            cursor.close()
            self._return_connection(conn)
            return deleted_ids
        except Exception as e:
            if 'conn' in locals():
                cursor.close()
                self._return_connection(conn)
            logger.error(f"Error getting deleted job IDs: {e}")
            return set()

    def add_job(self, job_data: Dict) -> Optional[int]:
        """
        Add a new job to the database

        Args:
            job_data: Dictionary containing job information

        Returns:
            Job ID if successful, None if job already exists or error occurred
        """
        try:
            from datetime import datetime
            import json
            import psycopg2

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
            return None  # Job already exists
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding job: {e}")
            return None
        finally:
            cursor.close()
            self._return_connection(conn)

    def delete_user_account(self, user_id: int) -> bool:
        """
        Permanently delete user account and all associated data.
        
        This will delete:
        - User record
        - All CVs (CASCADE)
        - All CV profiles (CASCADE)
        - All user-job matches (CASCADE)
        - All search history (CASCADE)
        - All applications (CASCADE)
        - All job feedback (CASCADE)
        - Physical CV files from disk
        
        Args:
            user_id: ID of the user to delete
            
        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Get CV file paths before deletion
            cursor.execute("""
                SELECT file_path FROM cvs WHERE user_id = %s
            """, (user_id,))
            cv_files = [row[0] for row in cursor.fetchall()]
            
            # Delete physical files
            import os
            for file_path in cv_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted CV file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")
            
            # Delete user (CASCADE will handle all related tables)
            cursor.execute("""
                DELETE FROM users WHERE id = %s
            """, (user_id,))
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"User {user_id} and all associated data deleted successfully")
                return True
            else:
                logger.warning(f"User {user_id} not found")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
            
        finally:
            cursor.close()
            self._return_connection(conn)

    def get_onboarding_status(self, user_id: int) -> dict:
        """
        Get user's onboarding progress
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with onboarding_completed, onboarding_step, onboarding_skipped
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT onboarding_completed, onboarding_step, onboarding_skipped
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            else:
                return {
                    'onboarding_completed': False,
                    'onboarding_step': 0,
                    'onboarding_skipped': False
                }
                
        except Exception as e:
            logger.error(f"Error getting onboarding status for user {user_id}: {e}")
            return {
                'onboarding_completed': False,
                'onboarding_step': 0,
                'onboarding_skipped': False
            }
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def update_onboarding_step(self, user_id: int, step: int) -> bool:
        """
        Update user's current onboarding step
        
        Args:
            user_id: User ID
            step: Current step number (0-5)
            
        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users
                SET onboarding_step = %s,
                    last_updated = %s
                WHERE id = %s
            """, (step, datetime.now(), user_id))
            
            conn.commit()
            logger.info(f"Updated onboarding step for user {user_id} to {step}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating onboarding step for user {user_id}: {e}")
            return False
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def complete_onboarding(self, user_id: int) -> bool:
        """
        Mark user's onboarding as completed
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users
                SET onboarding_completed = true,
                    onboarding_step = 5,
                    last_updated = %s
                WHERE id = %s
            """, (datetime.now(), user_id))
            
            conn.commit()
            logger.info(f"Marked onboarding as completed for user {user_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error completing onboarding for user {user_id}: {e}")
            return False
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    def skip_onboarding(self, user_id: int) -> bool:
        """
        Mark user's onboarding as skipped
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users
                SET onboarding_skipped = true,
                    onboarding_completed = true,
                    last_updated = %s
                WHERE id = %s
            """, (datetime.now(), user_id))
            
            conn.commit()
            logger.info(f"Marked onboarding as skipped for user {user_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error skipping onboarding for user {user_id}: {e}")
            return False
            
        finally:
            cursor.close()
            self._return_connection(conn)

    def close(self):
        """Close method for compatibility - connection pool managed by PostgresDatabase"""
        pass

