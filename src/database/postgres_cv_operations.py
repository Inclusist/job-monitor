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
    
    def authenticate_user(self, email: str, password: str) -> Optional[int]:
        """Authenticate user and return user ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            cursor.close()
            self._return_connection(conn)
            
            if not user:
                return None
            
            # Check password
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return user['id']
            
            return None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
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
                return profile_dict
            
            return None
            
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self._return_connection(conn)
            logger.error(f"Error getting CV profile: {e}")
            return None
