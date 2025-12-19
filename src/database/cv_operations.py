"""
CV Management Database Operations
Handles users, CVs, and CV profiles in SQLite database
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import os
from werkzeug.security import generate_password_hash, check_password_hash


class CVManager:
    def __init__(self, db_path: str = "data/jobs.db"):
        """Initialize database connection and create tables if needed"""
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
        """Create CV-related database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                name TEXT,
                current_role TEXT,
                location TEXT,
                created_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                preferences TEXT,
                last_filter_run TEXT,
                preferences_updated TEXT
            )
        """)

        # CVs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cvs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                uploaded_date TEXT NOT NULL,
                is_primary INTEGER DEFAULT 0,
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # CV Profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cv_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cv_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                technical_skills TEXT,
                soft_skills TEXT,
                languages TEXT,
                certifications TEXT,
                work_experience TEXT,
                total_years_experience REAL,
                leadership_experience TEXT,
                education TEXT,
                highest_degree TEXT,
                expertise_summary TEXT,
                career_highlights TEXT,
                industries TEXT,
                parsed_date TEXT NOT NULL,
                parsing_model TEXT,
                parsing_cost REAL,
                full_text TEXT,
                FOREIGN KEY (cv_id) REFERENCES cvs(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(cv_id)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cvs_user_id ON cvs(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cvs_is_primary ON cvs(user_id, is_primary)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cv_profiles_cv_id ON cv_profiles(cv_id)
        """)

        conn.commit()
        conn.close()

    # ==================== User Management ====================

    def add_user(self, email: str, name: str = None, current_role: str = None,
                 location: str = None, preferences: Dict = None) -> Optional[int]:
        """
        Add a new user to the database

        Args:
            email: User email (unique identifier)
            name: User's name
            current_role: Current job title
            location: User's location
            preferences: User preferences as dict

        Returns:
            User ID if successful, None if user already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO users (
                    email, name, current_role, location, created_date,
                    last_updated, preferences
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                email.lower(),
                name,
                current_role,
                location,
                now,
                now,
                json.dumps(preferences) if preferences else None
            ))

            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id

        except sqlite3.IntegrityError:
            # User already exists
            conn.close()
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            user = dict(row)
            # Parse JSON preferences
            if user.get('preferences'):
                user['preferences'] = json.loads(user['preferences'])
            return user
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            user = dict(row)
            if user.get('preferences'):
                user['preferences'] = json.loads(user['preferences'])
            return user
        return None

    def get_or_create_user(self, email: str, name: str = None, **kwargs) -> Dict:
        """
        Get existing user or create new one

        Returns:
            User dictionary
        """
        user = self.get_user_by_email(email)
        if user:
            return user

        user_id = self.add_user(email, name, **kwargs)
        return self.get_user_by_id(user_id)

    def update_user(self, user_id: int, **kwargs):
        """Update user fields"""
        conn = self._get_connection()
        cursor = conn.cursor()
        allowed_fields = ['name', 'current_role', 'location', 'is_active']
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
            elif field == 'preferences':
                updates.append("preferences = ?")
                values.append(json.dumps(value))

        if updates:
            updates.append("last_updated = ?")
            values.append(datetime.now().isoformat())
            values.append(user_id)

            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        conn.close()
    
    def update_filter_run_time(self, user_id: int):
        """Update last_filter_run timestamp for a user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE users SET last_filter_run = ?, last_updated = ?
            WHERE id = ?
        """, (now, now, user_id))
        conn.commit()
        conn.close()
    
    def update_preferences_time(self, user_id: int):
        """Update preferences_updated timestamp for a user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE users SET preferences_updated = ?, last_updated = ?
            WHERE id = ?
        """, (now, now, user_id))
        conn.commit()
        conn.close()
    
    def should_refilter(self, user_id: int) -> tuple:
        """
        Check if user needs re-filtering based on last run and preferences
        
        Returns:
            (should_refilter, reason)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT last_filter_run, preferences_updated
            FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return (True, "User not found")
        
        last_filter = row['last_filter_run']
        prefs_updated = row['preferences_updated']
        
        if not last_filter:
            return (True, "Never filtered")
        
        if prefs_updated and prefs_updated > last_filter:
            return (True, "Preferences changed since last filter")
        
        return (False, "Up to date")

    def get_all_active_users(self) -> List[Dict]:
        """Get all active users"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_active = 1")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        for user in users:
            if user.get('preferences'):
                user['preferences'] = json.loads(user['preferences'])
        return users
    
    # ============ Authentication Methods ============
    
    def register_user(self, email: str, password: str, name: str = None) -> Optional[int]:
        """
        Register a new user with email and password
        
        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            name: Optional user name
            
        Returns:
            user_id if successful, None if email already exists
        """
        # Check if email already exists
        existing_user = self.get_user_by_email(email)
        if existing_user:
            return None
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            password_hash = generate_password_hash(password)
            
            cursor.execute("""
                INSERT INTO users (
                    email, password_hash, name, created_date, last_updated
                ) VALUES (?, ?, ?, ?, ?)
            """, (email.lower(), password_hash, name, now, now))
            
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
            
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with email and password
        
        Args:
            email: User's email address
            password: Plain text password to check
            
        Returns:
            User dict if authentication successful, None otherwise
        """
        user = self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not user.get('password_hash'):
            return None
        
        if not user.get('is_active', 1):
            return None
        
        if check_password_hash(user['password_hash'], password):
            return user
        
        return None
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user's password
        
        Args:
            user_id: User ID
            new_password: New plain text password (will be hashed)
            
        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        password_hash = generate_password_hash(new_password)
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE users SET password_hash = ?, last_updated = ?
            WHERE id = ?
        """, (password_hash, now, user_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
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
                                      locations: List[str] = None):
        """
        Update user's search preferences
        
        Args:
            user_id: User ID
            keywords: List of job search keywords
            locations: List of locations to search
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return
        
        preferences = user.get('preferences') or {}
        if keywords is not None:
            preferences['search_keywords'] = keywords
        if locations is not None:
            preferences['search_locations'] = locations
        
        self.update_user(user_id, preferences=preferences)

    # ==================== CV Management ====================

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
            CV ID if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO cvs (
                    user_id, file_name, file_path, file_type, file_size,
                    file_hash, uploaded_date, version, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (
                user_id, file_name, file_path, file_type, file_size,
                file_hash, now, version
            ))

            conn.commit()
            cv_id = cursor.lastrowid
            conn.close()
            return cv_id

        except Exception as e:
            print(f"Error adding CV: {e}")
            conn.close()
            return None

    def get_cv(self, cv_id: int) -> Optional[Dict]:
        """Get CV by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cvs WHERE id = ?", (cv_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_cvs(self, user_id: int, status: str = 'active') -> List[Dict]:
        """
        Get all CVs for a user

        Args:
            user_id: User ID
            status: Filter by status ('active', 'archived', 'all')

        Returns:
            List of CV dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        if status == 'all':
            cursor.execute("""
                SELECT * FROM cvs
                WHERE user_id = ?
                ORDER BY uploaded_date DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM cvs
                WHERE user_id = ? AND status = ?
                ORDER BY uploaded_date DESC
            """, (user_id, status))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def set_primary_cv(self, user_id: int, cv_id: int):
        """
        Set a CV as primary (atomic transaction)

        Args:
            user_id: User ID
            cv_id: CV ID to set as primary
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Verify CV belongs to user
            cv = self.get_cv(cv_id)
            if not cv or cv['user_id'] != user_id:
                conn.close()
                raise ValueError("CV not found or doesn't belong to user")

            # Unset all primary flags for user
            cursor.execute(
                "UPDATE cvs SET is_primary = 0 WHERE user_id = ?",
                (user_id,)
            )

            # Set new primary
            cursor.execute(
                "UPDATE cvs SET is_primary = 1 WHERE id = ?",
                (cv_id,)
            )

            conn.commit()
            conn.close()

        except Exception as e:
            conn.rollback()
            conn.close()
            raise Exception(f"Failed to set primary CV: {e}")

    def get_primary_cv(self, user_id: int) -> Optional[Dict]:
        """Get user's primary CV"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM cvs
            WHERE user_id = ? AND is_primary = 1 AND status = 'active'
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def archive_cv(self, cv_id: int):
        """Archive a CV (soft delete)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cvs SET status = 'archived' WHERE id = ?",
            (cv_id,)
        )
        conn.commit()
        conn.close()

    def delete_cv(self, cv_id: int):
        """Delete a CV (hard delete - also removes associated profile)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cvs WHERE id = ?", (cv_id,))
        conn.commit()
        conn.close()

    def check_duplicate_hash(self, user_id: int, file_hash: str) -> Optional[Dict]:
        """Check if CV with same hash already exists"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM cvs
            WHERE user_id = ? AND file_hash = ? AND status = 'active'
        """, (user_id, file_hash))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_cv_status(self, cv_id: int, status: str):
        """Update CV status"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cvs SET status = ? WHERE id = ?",
            (status, cv_id)
        )
        conn.commit()
        conn.close()

    # ==================== CV Profile Management ====================

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
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO cv_profiles (
                cv_id, user_id, technical_skills, soft_skills, languages,
                certifications, work_experience, total_years_experience,
                leadership_experience, education, highest_degree,
                expertise_summary, career_highlights, industries,
                parsed_date, parsing_model, parsing_cost, full_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cv_id,
            user_id,
            json.dumps(profile_data.get('technical_skills', [])),
            json.dumps(profile_data.get('soft_skills', [])),
            json.dumps(profile_data.get('languages', [])),
            json.dumps(profile_data.get('certifications', [])),
            json.dumps(profile_data.get('work_experience', [])),
            profile_data.get('total_years_experience'),
            json.dumps(profile_data.get('leadership_experience', [])),
            json.dumps(profile_data.get('education', [])),
            profile_data.get('highest_degree'),
            profile_data.get('expertise_summary'),
            json.dumps(profile_data.get('career_highlights', [])),
            json.dumps(profile_data.get('industries', [])),
            now,
            profile_data.get('parsing_model'),
            profile_data.get('parsing_cost'),
            profile_data.get('full_text')
        ))

        conn.commit()
        profile_id = cursor.lastrowid
        conn.close()
        return profile_id

    def get_cv_profile(self, cv_id: int, include_full_text: bool = False) -> Optional[Dict]:
        """
        Get CV profile by CV ID

        Args:
            cv_id: CV ID
            include_full_text: Whether to include full extracted text
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        if include_full_text:
            cursor.execute("SELECT * FROM cv_profiles WHERE cv_id = ?", (cv_id,))
        else:
            # Exclude full_text for performance
            cursor.execute("""
                SELECT id, cv_id, user_id, technical_skills, soft_skills, languages,
                       certifications, work_experience, total_years_experience,
                       leadership_experience, education, highest_degree,
                       expertise_summary, career_highlights, industries,
                       parsed_date, parsing_model, parsing_cost
                FROM cv_profiles WHERE cv_id = ?
            """, (cv_id,))

        row = cursor.fetchone()
        conn.close()
        if row:
            profile = dict(row)
            # Parse JSON fields
            json_fields = [
                'technical_skills', 'soft_skills', 'languages', 'certifications',
                'work_experience', 'leadership_experience', 'education',
                'career_highlights', 'industries'
            ]
            for field in json_fields:
                if field in profile and profile[field]:
                    profile[field] = json.loads(profile[field])
            return profile
        return None

    def get_profile_by_user(self, user_id: int) -> Optional[Dict]:
        """Get primary CV profile for user"""
        # Get primary CV
        cv = self.get_primary_cv(user_id)
        if not cv:
            return None

        # Get profile for that CV
        profile = self.get_cv_profile(cv['id'])
        if profile:
            # Add CV metadata to profile
            profile['cv_file_name'] = cv['file_name']
            profile['uploaded_date'] = cv['uploaded_date']
        return profile

    def update_cv_profile(self, cv_id: int, profile_data: Dict):
        """Update CV profile data"""
        conn = self._get_connection()
        cursor = conn.cursor()
        updates = []
        values = []

        json_fields = {
            'technical_skills', 'soft_skills', 'languages', 'certifications',
            'work_experience', 'leadership_experience', 'education',
            'career_highlights', 'industries'
        }

        for field, value in profile_data.items():
            if field in json_fields:
                updates.append(f"{field} = ?")
                values.append(json.dumps(value))
            elif field in ['total_years_experience', 'highest_degree',
                          'expertise_summary', 'parsing_cost']:
                updates.append(f"{field} = ?")
                values.append(value)

        if updates:
            values.append(cv_id)
            query = f"UPDATE cv_profiles SET {', '.join(updates)} WHERE cv_id = ?"
            cursor.execute(query, values)
            conn.commit()
        conn.close()

    # ==================== Statistics ====================

    def get_cv_statistics(self) -> Dict[str, Any]:
        """Get CV system statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        stats = {}

        # User stats
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        stats['active_users'] = cursor.fetchone()[0]

        # CV stats
        cursor.execute("SELECT COUNT(*) FROM cvs WHERE status = 'active'")
        stats['total_cvs'] = cursor.fetchone()[0]

        # Parsing success rate
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'failed_parsing' THEN 1 ELSE 0 END) as failed
            FROM cvs
        """)
        row = cursor.fetchone()
        total, failed = row[0], row[1]
        stats['parsing_success_rate'] = (total - failed) / total if total > 0 else 0

        # Total parsing cost
        cursor.execute("SELECT SUM(parsing_cost) FROM cv_profiles")
        stats['total_parsing_cost'] = cursor.fetchone()[0] or 0.0

        # CVs per user
        cursor.execute("""
            SELECT AVG(cv_count), MIN(cv_count), MAX(cv_count)
            FROM (
                SELECT user_id, COUNT(*) as cv_count
                FROM cvs
                WHERE status = 'active'
                GROUP BY user_id
            )
        """)
        row = cursor.fetchone()
        if row[0]:
            stats['avg_cvs_per_user'] = round(row[0], 2)
            stats['min_cvs_per_user'] = row[1]
            stats['max_cvs_per_user'] = row[2]
        else:
            stats['avg_cvs_per_user'] = 0
            stats['min_cvs_per_user'] = 0
            stats['max_cvs_per_user'] = 0

        conn.close()
        return stats

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        stats = {}

        # Total CVs
        cursor.execute(
            "SELECT COUNT(*) FROM cvs WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        stats['total_cvs'] = cursor.fetchone()[0]

        # Primary CV info
        primary_cv = self.get_primary_cv(user_id)
        if primary_cv:
            stats['primary_cv_name'] = primary_cv['file_name']
            stats['primary_cv_uploaded'] = primary_cv['uploaded_date']
        else:
            stats['primary_cv_name'] = None

        # Latest upload
        cursor.execute("""
            SELECT MAX(uploaded_date) FROM cvs WHERE user_id = ?
        """, (user_id,))
        stats['latest_upload'] = cursor.fetchone()[0]
        
        conn.close()
        return stats

    def close(self):
        """Close database connection - no longer needed with thread-safe connections"""
        pass


if __name__ == "__main__":
    # Test the CV manager
    print("Testing CVManager...")

    cv_manager = CVManager("data/test_jobs.db")

    # Test adding a user
    user_id = cv_manager.add_user(
        email="test@example.com",
        name="Test User",
        current_role="Software Engineer",
        location="Berlin, Germany"
    )
    print(f"Created user with ID: {user_id}")

    # Get user
    user = cv_manager.get_user_by_email("test@example.com")
    print(f"Retrieved user: {user['name']}")

    # Test adding a CV
    cv_id = cv_manager.add_cv(
        user_id=user['id'],
        file_name="test_cv.pdf",
        file_path="data/cvs/test@example.com/test_cv.pdf",
        file_type="pdf",
        file_size=102400,
        file_hash="abc123def456"
    )
    print(f"Created CV with ID: {cv_id}")

    # Set as primary
    cv_manager.set_primary_cv(user['id'], cv_id)
    print("Set CV as primary")

    # Test adding profile
    profile_data = {
        'technical_skills': ['Python', 'SQL', 'Machine Learning'],
        'soft_skills': ['Leadership', 'Communication'],
        'languages': [{'language': 'English', 'level': 'C1'}],
        'total_years_experience': 5.0,
        'expertise_summary': 'Experienced software engineer',
        'parsing_model': 'claude-3-5-sonnet-20241022',
        'parsing_cost': 0.02
    }

    profile_id = cv_manager.add_cv_profile(cv_id, user['id'], profile_data)
    print(f"Created profile with ID: {profile_id}")

    # Get statistics
    stats = cv_manager.get_cv_statistics()
    print(f"Statistics: {stats}")

    cv_manager.close()
    print("CVManager test completed successfully!")
