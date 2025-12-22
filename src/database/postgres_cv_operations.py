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
        """Get a connection from the pool"""
        return self.connection_pool.getconn()
    
    def _return_connection(self, conn):
        """Return connection to pool"""
        self.connection_pool.putconn(conn)
    
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
            
            cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
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
        """Get user by email"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
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
        Check if user needs re-filtering based on last run and preferences
        
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
            
            cursor.close()
            self._return_connection(conn)
            
            if not row:
                return (True, "User not found")
            
            last_filter = row['last_filter_run']
            prefs_updated = row['preferences_updated']
            
            if not last_filter:
                return (True, "Never filtered")
            
            if prefs_updated and prefs_updated > last_filter:
                return (True, "Preferences changed since last filter")
            
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
                    cv_id, user_id, technical_skills, soft_skills, languages,
                    education, work_history, achievements, expertise_summary,
                    career_level, preferred_roles, industries, raw_analysis,
                    created_date, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                cv_id, user_id,
                json.dumps(profile_data.get('technical_skills', [])),
                json.dumps(profile_data.get('soft_skills', [])),
                json.dumps(profile_data.get('languages', [])),
                json.dumps(profile_data.get('education', [])),
                json.dumps(profile_data.get('work_history', [])),
                json.dumps(profile_data.get('achievements', [])),
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
                    raw_analysis, created_date, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                json.dumps(profile_data.get('full_text', profile_data.get('raw_analysis', {}))),
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

