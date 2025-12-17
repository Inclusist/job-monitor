"""
CV Management Database Operations
Handles users, CVs, and CV profiles in SQLite database
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import os


class CVManager:
    def __init__(self, db_path: str = "data/jobs.db"):
        """Initialize database connection and create tables if needed"""
        self.db_path = db_path

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create CV-related database tables if they don't exist"""

        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                current_role TEXT,
                location TEXT,
                created_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                preferences TEXT
            )
        """)

        # CVs table
        self.cursor.execute("""
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
        self.cursor.execute("""
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
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cvs_user_id ON cvs(user_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cvs_is_primary ON cvs(user_id, is_primary)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cv_profiles_cv_id ON cv_profiles(cv_id)
        """)

        self.conn.commit()

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
        try:
            now = datetime.now().isoformat()

            self.cursor.execute("""
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

            self.conn.commit()
            return self.cursor.lastrowid

        except sqlite3.IntegrityError:
            # User already exists
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        self.cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = self.cursor.fetchone()
        if row:
            user = dict(row)
            # Parse JSON preferences
            if user.get('preferences'):
                user['preferences'] = json.loads(user['preferences'])
            return user
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
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
            self.cursor.execute(query, values)
            self.conn.commit()

    def get_all_active_users(self) -> List[Dict]:
        """Get all active users"""
        self.cursor.execute("SELECT * FROM users WHERE is_active = 1")
        users = [dict(row) for row in self.cursor.fetchall()]
        for user in users:
            if user.get('preferences'):
                user['preferences'] = json.loads(user['preferences'])
        return users

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
        try:
            now = datetime.now().isoformat()

            self.cursor.execute("""
                INSERT INTO cvs (
                    user_id, file_name, file_path, file_type, file_size,
                    file_hash, uploaded_date, version, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (
                user_id, file_name, file_path, file_type, file_size,
                file_hash, now, version
            ))

            self.conn.commit()
            return self.cursor.lastrowid

        except Exception as e:
            print(f"Error adding CV: {e}")
            return None

    def get_cv(self, cv_id: int) -> Optional[Dict]:
        """Get CV by ID"""
        self.cursor.execute("SELECT * FROM cvs WHERE id = ?", (cv_id,))
        row = self.cursor.fetchone()
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
        if status == 'all':
            self.cursor.execute("""
                SELECT * FROM cvs
                WHERE user_id = ?
                ORDER BY uploaded_date DESC
            """, (user_id,))
        else:
            self.cursor.execute("""
                SELECT * FROM cvs
                WHERE user_id = ? AND status = ?
                ORDER BY uploaded_date DESC
            """, (user_id, status))

        return [dict(row) for row in self.cursor.fetchall()]

    def set_primary_cv(self, user_id: int, cv_id: int):
        """
        Set a CV as primary (atomic transaction)

        Args:
            user_id: User ID
            cv_id: CV ID to set as primary
        """
        try:
            # Verify CV belongs to user
            cv = self.get_cv(cv_id)
            if not cv or cv['user_id'] != user_id:
                raise ValueError("CV not found or doesn't belong to user")

            # Unset all primary flags for user
            self.cursor.execute(
                "UPDATE cvs SET is_primary = 0 WHERE user_id = ?",
                (user_id,)
            )

            # Set new primary
            self.cursor.execute(
                "UPDATE cvs SET is_primary = 1 WHERE id = ?",
                (cv_id,)
            )

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to set primary CV: {e}")

    def get_primary_cv(self, user_id: int) -> Optional[Dict]:
        """Get user's primary CV"""
        self.cursor.execute("""
            SELECT * FROM cvs
            WHERE user_id = ? AND is_primary = 1 AND status = 'active'
        """, (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def archive_cv(self, cv_id: int):
        """Archive a CV (soft delete)"""
        self.cursor.execute(
            "UPDATE cvs SET status = 'archived' WHERE id = ?",
            (cv_id,)
        )
        self.conn.commit()

    def delete_cv(self, cv_id: int):
        """Delete a CV (hard delete - also removes associated profile)"""
        self.cursor.execute("DELETE FROM cvs WHERE id = ?", (cv_id,))
        self.conn.commit()

    def check_duplicate_hash(self, user_id: int, file_hash: str) -> Optional[Dict]:
        """Check if CV with same hash already exists"""
        self.cursor.execute("""
            SELECT * FROM cvs
            WHERE user_id = ? AND file_hash = ? AND status = 'active'
        """, (user_id, file_hash))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_cv_status(self, cv_id: int, status: str):
        """Update CV status"""
        self.cursor.execute(
            "UPDATE cvs SET status = ? WHERE id = ?",
            (status, cv_id)
        )
        self.conn.commit()

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
        now = datetime.now().isoformat()

        self.cursor.execute("""
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

        self.conn.commit()
        return self.cursor.lastrowid

    def get_cv_profile(self, cv_id: int, include_full_text: bool = False) -> Optional[Dict]:
        """
        Get CV profile by CV ID

        Args:
            cv_id: CV ID
            include_full_text: Whether to include full extracted text
        """
        if include_full_text:
            self.cursor.execute("SELECT * FROM cv_profiles WHERE cv_id = ?", (cv_id,))
        else:
            # Exclude full_text for performance
            self.cursor.execute("""
                SELECT id, cv_id, user_id, technical_skills, soft_skills, languages,
                       certifications, work_experience, total_years_experience,
                       leadership_experience, education, highest_degree,
                       expertise_summary, career_highlights, industries,
                       parsed_date, parsing_model, parsing_cost
                FROM cv_profiles WHERE cv_id = ?
            """, (cv_id,))

        row = self.cursor.fetchone()
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
            self.cursor.execute(query, values)
            self.conn.commit()

    # ==================== Statistics ====================

    def get_cv_statistics(self) -> Dict[str, Any]:
        """Get CV system statistics"""
        stats = {}

        # User stats
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        stats['active_users'] = self.cursor.fetchone()[0]

        # CV stats
        self.cursor.execute("SELECT COUNT(*) FROM cvs WHERE status = 'active'")
        stats['total_cvs'] = self.cursor.fetchone()[0]

        # Parsing success rate
        self.cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'failed_parsing' THEN 1 ELSE 0 END) as failed
            FROM cvs
        """)
        row = self.cursor.fetchone()
        total, failed = row[0], row[1]
        stats['parsing_success_rate'] = (total - failed) / total if total > 0 else 0

        # Total parsing cost
        self.cursor.execute("SELECT SUM(parsing_cost) FROM cv_profiles")
        stats['total_parsing_cost'] = self.cursor.fetchone()[0] or 0.0

        # CVs per user
        self.cursor.execute("""
            SELECT AVG(cv_count), MIN(cv_count), MAX(cv_count)
            FROM (
                SELECT user_id, COUNT(*) as cv_count
                FROM cvs
                WHERE status = 'active'
                GROUP BY user_id
            )
        """)
        row = self.cursor.fetchone()
        if row[0]:
            stats['avg_cvs_per_user'] = round(row[0], 2)
            stats['min_cvs_per_user'] = row[1]
            stats['max_cvs_per_user'] = row[2]
        else:
            stats['avg_cvs_per_user'] = 0
            stats['min_cvs_per_user'] = 0
            stats['max_cvs_per_user'] = 0

        return stats

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        stats = {}

        # Total CVs
        self.cursor.execute(
            "SELECT COUNT(*) FROM cvs WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        stats['total_cvs'] = self.cursor.fetchone()[0]

        # Primary CV info
        primary_cv = self.get_primary_cv(user_id)
        if primary_cv:
            stats['primary_cv_name'] = primary_cv['file_name']
            stats['primary_cv_uploaded'] = primary_cv['uploaded_date']
        else:
            stats['primary_cv_name'] = None

        # Latest upload
        self.cursor.execute("""
            SELECT MAX(uploaded_date) FROM cvs WHERE user_id = ?
        """, (user_id,))
        stats['latest_upload'] = self.cursor.fetchone()[0]

        return stats

    def close(self):
        """Close database connection"""
        self.conn.close()


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
