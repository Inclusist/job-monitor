"""
PostgreSQL Resume Operations

Handles database operations for resume generation feature:
- Save/retrieve user-claimed competencies and skills with evidence
- Save/retrieve generated resumes
- Update CV profiles with claimed data
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class PostgresResumeOperations:
    """Handle resume-related database operations"""

    def __init__(self, connection_pool):
        """
        Initialize with database connection pool

        Args:
            connection_pool: psycopg2 connection pool
        """
        self.pool = connection_pool

    def save_user_claimed_competency(self, user_id: int, competency_name: str,
                                     work_exp_ids: List[int], evidence: str) -> bool:
        """
        Save user's claimed competency with evidence

        Args:
            user_id: User ID
            competency_name: Name of the competency being claimed
            work_exp_ids: List of work experience IDs where this was demonstrated
            evidence: User's description of how they demonstrated this

        Returns:
            bool: True if successful
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            # Get current claimed competencies
            cursor.execute("""
                SELECT user_claimed_competencies
                FROM cv_profiles
                WHERE user_id = %s
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"No CV profile found for user {user_id}")

            claimed_competencies = row[0] or {}

            # Add/update the competency
            claimed_competencies[competency_name] = {
                'work_experience_ids': work_exp_ids,
                'evidence': evidence,
                'added_at': datetime.now().isoformat()
            }

            # Update database
            cursor.execute("""
                UPDATE cv_profiles
                SET user_claimed_competencies = %s,
                    last_updated = NOW()
                WHERE user_id = %s
            """, (json.dumps(claimed_competencies), user_id))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print(f"Error saving claimed competency: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def save_user_claimed_skill(self, user_id: int, skill_name: str,
                                work_exp_ids: List[int], evidence: str) -> bool:
        """
        Save user's claimed skill with evidence

        Args:
            user_id: User ID
            skill_name: Name of the skill being claimed
            work_exp_ids: List of work experience IDs where this was demonstrated
            evidence: User's description of how they demonstrated this

        Returns:
            bool: True if successful
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            # Get current claimed skills
            cursor.execute("""
                SELECT user_claimed_skills
                FROM cv_profiles
                WHERE user_id = %s
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"No CV profile found for user {user_id}")

            claimed_skills = row[0] or {}

            # Add/update the skill
            claimed_skills[skill_name] = {
                'work_experience_ids': work_exp_ids,
                'evidence': evidence,
                'added_at': datetime.now().isoformat()
            }

            # Update database
            cursor.execute("""
                UPDATE cv_profiles
                SET user_claimed_skills = %s,
                    last_updated = NOW()
                WHERE user_id = %s
            """, (json.dumps(claimed_skills), user_id))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print(f"Error saving claimed skill: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def save_multiple_claims(self, user_id: int, selections: List[Dict[str, Any]]) -> bool:
        """
        Save multiple competency/skill claims in a single transaction

        Args:
            user_id: User ID
            selections: List of dicts with keys: name, type, work_experience_ids, evidence

        Returns:
            bool: True if successful
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            # Get current claimed data
            cursor.execute("""
                SELECT user_claimed_competencies, user_claimed_skills
                FROM cv_profiles
                WHERE user_id = %s
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"No CV profile found for user {user_id}")

            claimed_competencies = row[0] or {}
            claimed_skills = row[1] or {}

            # Process each selection
            for selection in selections:
                item_data = {
                    'work_experience_ids': selection.get('work_experience_ids', []),
                    'evidence': selection.get('evidence', ''),
                    'added_at': datetime.now().isoformat()
                }

                if selection['type'] == 'competency':
                    claimed_competencies[selection['name']] = item_data
                else:  # skill
                    claimed_skills[selection['name']] = item_data

            # Update database with both in one transaction
            cursor.execute("""
                UPDATE cv_profiles
                SET user_claimed_competencies = %s,
                    user_claimed_skills = %s,
                    last_updated = NOW()
                WHERE user_id = %s
            """, (json.dumps(claimed_competencies), json.dumps(claimed_skills), user_id))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print(f"Error saving multiple claims: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_user_claimed_data(self, user_id: int) -> Dict[str, Dict]:
        """
        Get all user's claimed competencies and skills

        Args:
            user_id: User ID

        Returns:
            Dict with 'competencies' and 'skills' keys containing claimed data
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_claimed_competencies, user_claimed_skills
                FROM cv_profiles
                WHERE user_id = %s
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return {'competencies': {}, 'skills': {}}

            return {
                'competencies': row[0] or {},
                'skills': row[1] or {}
            }

        finally:
            cursor.close()
            self.pool.putconn(conn)

    def remove_claimed_competency(self, user_id: int, competency_name: str) -> bool:
        """
        Remove a claimed competency

        Args:
            user_id: User ID
            competency_name: Name of competency to remove

        Returns:
            bool: True if successful
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_claimed_competencies
                FROM cv_profiles
                WHERE user_id = %s
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"No CV profile found for user {user_id}")

            claimed_competencies = row[0] or {}

            if competency_name in claimed_competencies:
                del claimed_competencies[competency_name]

                cursor.execute("""
                    UPDATE cv_profiles
                    SET user_claimed_competencies = %s,
                        last_updated = NOW()
                    WHERE user_id = %s
                """, (json.dumps(claimed_competencies), user_id))

                conn.commit()

            return True

        except Exception as e:
            conn.rollback()
            print(f"Error removing claimed competency: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def remove_claimed_skill(self, user_id: int, skill_name: str) -> bool:
        """
        Remove a claimed skill

        Args:
            user_id: User ID
            skill_name: Name of skill to remove

        Returns:
            bool: True if successful
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_claimed_skills
                FROM cv_profiles
                WHERE user_id = %s
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"No CV profile found for user {user_id}")

            claimed_skills = row[0] or {}

            if skill_name in claimed_skills:
                del claimed_skills[skill_name]

                cursor.execute("""
                    UPDATE cv_profiles
                    SET user_claimed_skills = %s,
                        last_updated = NOW()
                    WHERE user_id = %s
                """, (json.dumps(claimed_skills), user_id))

                conn.commit()

            return True

        except Exception as e:
            conn.rollback()
            print(f"Error removing claimed skill: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def save_generated_resume(self, user_id: int, job_id: int, resume_html: str,
                             resume_pdf_path: Optional[str],
                             selections_used: Dict[str, Any],
                             pdf_data: Optional[bytes] = None) -> int:
        """
        Save generated resume to database

        Args:
            user_id: User ID
            job_id: Job ID
            resume_html: Generated HTML content
            resume_pdf_path: Path to generated PDF file (legacy, kept for compat)
            selections_used: Dict of claimed competencies/skills used in this resume
            pdf_data: Raw PDF bytes to persist (preferred over pdf_path)

        Returns:
            int: Resume ID
        """
        import psycopg2
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            # Check if resume already exists for this user/job
            cursor.execute("""
                SELECT id FROM user_generated_resumes
                WHERE user_id = %s AND job_id = %s
            """, (user_id, job_id))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE user_generated_resumes
                    SET resume_html = %s,
                        resume_pdf_path = %s,
                        resume_pdf_data = %s,
                        selections_used = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                """, (resume_html, resume_pdf_path,
                      psycopg2.Binary(pdf_data) if pdf_data else None,
                      json.dumps(selections_used), existing[0]))
            else:
                cursor.execute("""
                    INSERT INTO user_generated_resumes
                        (user_id, job_id, resume_html, resume_pdf_path, resume_pdf_data, selections_used)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, job_id, resume_html, resume_pdf_path,
                      psycopg2.Binary(pdf_data) if pdf_data else None,
                      json.dumps(selections_used)))

            resume_id = cursor.fetchone()[0]
            conn.commit()
            return resume_id

        except Exception as e:
            conn.rollback()
            print(f"Error saving generated resume: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_user_resumes(self, user_id: int, job_id: Optional[int] = None) -> List[Dict]:
        """
        Get user's generated resumes

        Args:
            user_id: User ID
            job_id: Optional job ID to filter by specific job

        Returns:
            List of resume dicts
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            if job_id:
                cursor.execute("""
                    SELECT id, user_id, job_id, resume_html, resume_pdf_path,
                           selections_used, created_at, updated_at, resume_pdf_data
                    FROM user_generated_resumes
                    WHERE user_id = %s AND job_id = %s
                    ORDER BY created_at DESC
                """, (user_id, job_id))
            else:
                cursor.execute("""
                    SELECT id, user_id, job_id, resume_html, resume_pdf_path,
                           selections_used, created_at, updated_at, resume_pdf_data
                    FROM user_generated_resumes
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))

            rows = cursor.fetchall()
            resumes = []

            for row in rows:
                resumes.append({
                    'id': row[0],
                    'user_id': row[1],
                    'job_id': row[2],
                    'resume_html': row[3],
                    'resume_pdf_path': row[4],
                    'selections_used': row[5] or {},
                    'created_at': row[6],
                    'updated_at': row[7],
                    'resume_pdf_data': bytes(row[8]) if row[8] else None,
                })

            return resumes

        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_resume_by_id(self, resume_id: int, user_id: int) -> Optional[Dict]:
        """
        Get specific resume by ID (with user verification)

        Args:
            resume_id: Resume ID
            user_id: User ID (for security check)

        Returns:
            Resume dict or None if not found/not owned by user
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, user_id, job_id, resume_html, resume_pdf_path,
                       selections_used, created_at, updated_at, resume_pdf_data
                FROM user_generated_resumes
                WHERE id = %s AND user_id = %s
            """, (resume_id, user_id))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row[0],
                'user_id': row[1],
                'job_id': row[2],
                'resume_html': row[3],
                'resume_pdf_path': row[4],
                'selections_used': row[5] or {},
                'created_at': row[6],
                'updated_at': row[7],
                'resume_pdf_data': bytes(row[8]) if row[8] else None,
            }

        finally:
            cursor.close()
            self.pool.putconn(conn)

    def delete_resume(self, resume_id: int, user_id: int) -> bool:
        """
        Delete a generated resume (with user verification)

        Args:
            resume_id: Resume ID
            user_id: User ID (for security check)

        Returns:
            bool: True if deleted
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM user_generated_resumes
                WHERE id = %s AND user_id = %s
                RETURNING id
            """, (resume_id, user_id))

            deleted = cursor.fetchone()
            conn.commit()

            return deleted is not None

        except Exception as e:
            conn.rollback()
            print(f"Error deleting resume: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_resume_count_for_user(self, user_id: int) -> int:
        """
        Get count of resumes generated by user

        Args:
            user_id: User ID

        Returns:
            int: Number of resumes
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM user_generated_resumes
                WHERE user_id = %s
            """, (user_id,))

            return cursor.fetchone()[0]

        finally:
            cursor.close()
            self.pool.putconn(conn)
