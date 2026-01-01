"""
CV Handler - Orchestrates complete CV upload and management workflow
"""

import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

from src.database.cv_operations import CVManager
from src.parsers.cv_parser import CVParser
from src.analysis.cv_analyzer import CVAnalyzer


class CVHandler:
    def __init__(self, cv_manager: CVManager, parser: CVParser,
                 analyzer: CVAnalyzer, storage_root: str = "data/cvs"):
        """
        Initialize CV Handler

        Args:
            cv_manager: CVManager instance for database operations
            parser: CVParser instance for text extraction
            analyzer: CVAnalyzer instance for Claude parsing
            storage_root: Root directory for CV storage
        """
        self.cv_manager = cv_manager
        self.parser = parser
        self.analyzer = analyzer
        self.storage_root = storage_root

        # Ensure storage root exists
        os.makedirs(storage_root, exist_ok=True)

    def upload_cv(self, user_email: str, file_path: str,
                  set_as_primary: bool = True) -> Dict[str, Any]:
        """
        Complete CV upload workflow

        Args:
            user_email: User's email
            file_path: Path to CV file to upload
            set_as_primary: Whether to set as primary CV

        Returns:
            Dictionary with upload result:
            {
                'success': True/False,
                'cv_id': int,
                'profile_id': int,
                'message': str,
                'parsing_cost': float
            }
        """
        try:
            # Step 1: Validate file
            is_valid, error_msg = self.parser.validate_cv_file(file_path)
            if not is_valid:
                return {
                    'success': False,
                    'message': f"File validation failed: {error_msg}"
                }

            # Step 2: Get or create user
            user = self.cv_manager.get_or_create_user(email=user_email)
            user_id = user['id']

            # Step 3: Calculate file hash for duplicate detection
            file_hash = self.parser.calculate_hash(file_path)

            # Check for duplicates
            duplicate = self.cv_manager.check_duplicate_hash(user_id, file_hash)
            if duplicate:
                return {
                    'success': False,
                    'message': f"CV already exists (uploaded: {duplicate['uploaded_date']})",
                    'existing_cv_id': duplicate['id']
                }

            # Step 4: Prepare file storage
            user_dir = os.path.join(self.storage_root, self._sanitize_email(user_email))
            os.makedirs(user_dir, exist_ok=True)

            # Get file info
            file_info = self.parser.get_file_info(file_path)

            # Determine version number
            version = self._get_next_version(user_id)

            # Generate new filename
            base_name = os.path.splitext(file_info['file_name'])[0]
            base_name = self._sanitize_filename(base_name)
            date_str = datetime.now().strftime('%Y-%m-%d')
            ext = f".{file_info['file_type']}"

            new_filename = f"{base_name}_{date_str}_v{version}{ext}"
            dest_path = os.path.join(user_dir, new_filename)

            # Step 5: Copy file to storage
            shutil.copy2(file_path, dest_path)

            # Calculate relative path for database
            rel_path = os.path.relpath(dest_path)

            # Step 6: Extract text
            print(f"Extracting text from {file_info['file_name']}...")
            text, extraction_status = self.parser.extract_text(dest_path)

            if extraction_status == 'failed':
                # Mark CV but don't fail upload
                cv_id = self.cv_manager.add_cv(
                    user_id=user_id,
                    file_name=new_filename,
                    file_path=rel_path,
                    file_type=file_info['file_type'],
                    file_size=file_info['file_size'],
                    file_hash=file_hash,
                    version=version
                )
                self.cv_manager.update_cv_status(cv_id, 'failed_parsing')

                return {
                    'success': False,
                    'cv_id': cv_id,
                    'message': 'CV uploaded but text extraction failed'
                }

            # Save extracted text
            text_filename = f"{base_name}_{date_str}_v{version}_extracted.txt"
            text_path = os.path.join(user_dir, text_filename)
            self.parser.save_extracted_text(text, text_path)

            # Step 7: Parse with Claude
            print(f"Analyzing CV with Claude AI...")
            profile_data = self.analyzer.analyze_cv(text, user_email)

            # Step 8: Store in database
            cv_id = self.cv_manager.add_cv(
                user_id=user_id,
                file_name=new_filename,
                file_path=rel_path,
                file_type=file_info['file_type'],
                file_size=file_info['file_size'],
                file_hash=file_hash,
                version=version
            )

            if not cv_id:
                return {
                    'success': False,
                    'message': 'Failed to store CV in database'
                }

            # Store profile
            profile_id = self.cv_manager.add_cv_profile(
                cv_id=cv_id,
                user_id=user_id,
                profile_data=profile_data
            )

            # Step 9: Set as primary if requested
            if set_as_primary:
                self.cv_manager.set_primary_cv(user_id, cv_id)

            # Step 10: Auto-generate search preferences if user has none
            self._auto_generate_search_preferences(user_id, profile_data, user_email)

            return {
                'success': True,
                'cv_id': cv_id,
                'profile_id': profile_id,
                'message': 'CV uploaded and analyzed successfully',
                'parsing_cost': profile_data.get('parsing_cost', 0.0),
                'extraction_status': extraction_status,
                'is_primary': set_as_primary
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error during upload: {str(e)}'
            }

    def get_user_cvs(self, user_email: str) -> List[Dict]:
        """
        Get all CVs for a user

        Args:
            user_email: User's email

        Returns:
            List of CV dictionaries
        """
        user = self.cv_manager.get_user_by_email(user_email)
        if not user:
            return []

        return self.cv_manager.get_user_cvs(user['id'])

    def get_primary_cv(self, user_email: str) -> Optional[Dict]:
        """
        Get user's primary CV with profile

        Args:
            user_email: User's email

        Returns:
            CV dictionary with profile data
        """
        user = self.cv_manager.get_user_by_email(user_email)
        if not user:
            return None

        cv = self.cv_manager.get_primary_cv(user['id'])
        if not cv:
            return None

        # Get profile
        profile = self.cv_manager.get_cv_profile(cv['id'])
        if profile:
            cv['profile'] = profile

        return cv

    def switch_primary_cv(self, user_email: str, cv_id: int) -> Dict[str, Any]:
        """
        Change which CV is primary

        Args:
            user_email: User's email
            cv_id: CV ID to set as primary

        Returns:
            Result dictionary
        """
        try:
            user = self.cv_manager.get_user_by_email(user_email)
            if not user:
                return {'success': False, 'message': 'User not found'}

            self.cv_manager.set_primary_cv(user['id'], cv_id)

            return {
                'success': True,
                'message': f'CV {cv_id} set as primary'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error setting primary CV: {str(e)}'
            }

    def delete_cv(self, user_email: str, cv_id: int, delete_files: bool = True) -> Dict[str, Any]:
        """
        Delete a CV

        Args:
            user_email: User's email
            cv_id: CV ID to delete
            delete_files: Whether to delete associated files

        Returns:
            Result dictionary
        """
        try:
            user = self.cv_manager.get_user_by_email(user_email)
            if not user:
                return {'success': False, 'message': 'User not found'}

            # Get CV info before deleting
            cv = self.cv_manager.get_cv(cv_id)
            if not cv:
                return {'success': False, 'message': 'CV not found'}

            # Verify CV belongs to user
            if cv['user_id'] != user['id']:
                return {'success': False, 'message': 'CV does not belong to user'}

            # Delete from database (cascades to profile)
            self.cv_manager.delete_cv(cv_id)

            # Delete files if requested
            if delete_files and cv['file_path']:
                try:
                    # Delete CV file
                    if os.path.exists(cv['file_path']):
                        os.remove(cv['file_path'])

                    # Delete extracted text file
                    text_path = cv['file_path'].replace(
                        f".{cv['file_type']}",
                        "_extracted.txt"
                    )
                    if os.path.exists(text_path):
                        os.remove(text_path)

                except Exception as e:
                    print(f"Warning: Could not delete files: {e}")

            return {
                'success': True,
                'message': f'CV {cv_id} deleted successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error deleting CV: {str(e)}'
            }

    def reparse_cv(self, cv_id: int) -> Dict[str, Any]:
        """
        Re-run Claude parsing on existing CV (useful after prompt improvements)

        Args:
            cv_id: CV ID to reparse

        Returns:
            Result dictionary
        """
        try:
            cv = self.cv_manager.get_cv(cv_id)
            if not cv:
                return {'success': False, 'message': 'CV not found'}

            # Get user
            user = self.cv_manager.get_user_by_id(cv['user_id'])
            if not user:
                return {'success': False, 'message': 'User not found'}

            # Extract text again
            text, status = self.parser.extract_text(cv['file_path'])
            if status == 'failed':
                return {'success': False, 'message': 'Text extraction failed'}

            # Re-analyze with Claude
            print(f"Re-analyzing CV {cv_id} with Claude...")
            profile_data = self.analyzer.analyze_cv(text, user['email'])

            # Update profile
            self.cv_manager.update_cv_profile(cv_id, profile_data)

            # Update CV status to active
            self.cv_manager.update_cv_status(cv_id, 'active')

            return {
                'success': True,
                'message': 'CV reparsed successfully',
                'parsing_cost': profile_data.get('parsing_cost', 0.0)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error reparsing CV: {str(e)}'
            }

    def get_cv_statistics(self, user_email: str = None) -> Dict[str, Any]:
        """
        Get CV statistics

        Args:
            user_email: Optional - get stats for specific user

        Returns:
            Statistics dictionary
        """
        if user_email:
            user = self.cv_manager.get_user_by_email(user_email)
            if not user:
                return {'error': 'User not found'}
            return self.cv_manager.get_user_statistics(user['id'])
        else:
            return self.cv_manager.get_cv_statistics()

    # ==================== Helper Methods ====================

    def _sanitize_email(self, email: str) -> str:
        """
        Sanitize email for use as directory name

        Args:
            email: Email address

        Returns:
            Sanitized email
        """
        # Email is already safe for directory names, just lowercase it
        return email.lower()

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to remove special characters

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')

        # Remove special characters except dots, dashes, underscores
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)

        # Limit length
        if len(filename) > 50:
            filename = filename[:50]

        return filename

    def _get_next_version(self, user_id: int) -> int:
        """
        Get next version number for user's CVs

        Args:
            user_id: User ID

        Returns:
            Next version number
        """
        cvs = self.cv_manager.get_user_cvs(user_id, status='all')
        if not cvs:
            return 1

        max_version = max(cv.get('version', 1) for cv in cvs)
        return max_version + 1

    def _auto_generate_search_preferences(self, user_id: int, profile_data: Dict, user_email: str) -> None:
        """
        Auto-generate search preferences from CV profile if user has none

        Args:
            user_id: User ID
            profile_data: Parsed CV profile data
            user_email: User's email for logging
        """
        try:
            # Check if user already has search preferences
            current_prefs = self.cv_manager.get_user_search_preferences(user_id)

            if current_prefs and (current_prefs.get('keywords') or current_prefs.get('locations')):
                print(f"User {user_email} already has search preferences, skipping auto-generation")
                return

            # Extract preferences from CV profile
            desired_titles = profile_data.get('desired_job_titles', [])
            preferred_locations = profile_data.get('preferred_work_locations', [])
            current_location = profile_data.get('current_location')

            # Prepare keywords (job titles)
            keywords = []
            if desired_titles:
                keywords = desired_titles[:5]  # Limit to top 5
                print(f"Auto-generated {len(keywords)} job keywords from CV: {keywords}")

            # Prepare locations
            locations = []
            if preferred_locations:
                locations = preferred_locations[:5]  # Limit to top 5
                print(f"Auto-generated {len(locations)} locations from CV: {locations}")

            # If no locations found, use current location
            if not locations and current_location:
                locations = [current_location]
                print(f"Using current location from CV: {current_location}")

            # Only update if we have at least keywords or locations
            if keywords or locations:
                self.cv_manager.update_user_search_preferences(
                    user_id=user_id,
                    keywords=keywords,
                    locations=locations
                )
                print(f"✓ Auto-generated search preferences for {user_email}")
                print(f"  Keywords: {len(keywords)}, Locations: {len(locations)}")
            else:
                print(f"No search preferences could be auto-generated from CV for {user_email}")

            # Update user location if available
            if current_location:
                self.cv_manager.update_user_location(user_id, current_location)
                print(f"✓ Updated user location to: {current_location}")

            # NEW: Auto-generate search queries
            self._auto_generate_search_queries(user_id, profile_data, user_email)

        except Exception as e:
            print(f"Warning: Could not auto-generate search preferences for {user_email}: {e}")
            # Don't fail the upload if this fails

    def _auto_generate_search_queries(self, user_id: int, profile_data: Dict, user_email: str) -> None:
        """
        Auto-generate personalized search queries using pipe operators

        Args:
            user_id: User ID
            profile_data: Parsed CV profile data
            user_email: User's email for logging
        """
        try:
            # Check if user already has search queries
            existing_queries = self.cv_manager.get_user_search_queries(user_id)

            if existing_queries:
                print(f"User {user_email} already has {len(existing_queries)} search queries, skipping auto-generation")
                return

            # Extract data from CV profile
            desired_titles = profile_data.get('desired_job_titles', [])
            preferred_locations = profile_data.get('preferred_work_locations', [])
            current_location = profile_data.get('current_location')
            work_arrangement = profile_data.get('work_arrangement_preference', 'flexible')
            industries = profile_data.get('industries', [])

            # Determine seniority from years of experience
            years_exp = profile_data.get('total_years_experience', 0)
            if years_exp >= 10:
                seniority = 'Senior|Lead'
            elif years_exp >= 5:
                seniority = 'Mid|Senior'
            elif years_exp >= 2:
                seniority = 'Mid'
            else:
                seniority = None

            # Build title_keywords using pipe operator
            title_keywords = None
            if desired_titles:
                title_keywords = '|'.join(desired_titles[:5])  # Top 5 titles
                print(f"Generated title keywords: {title_keywords}")

            # Build locations using pipe operator
            locations_str = None
            location_list = []

            # Add preferred locations
            if preferred_locations:
                location_list.extend(preferred_locations[:3])

            # Add current location if not in preferred
            if current_location and current_location not in location_list:
                location_list.append(current_location)

            if location_list:
                locations_str = '|'.join(location_list)
                print(f"Generated locations: {locations_str}")

            # Build work arrangement filter
            work_filter = None
            if work_arrangement and work_arrangement != 'flexible':
                # Map CV preferences to API filter values
                work_map = {
                    'remote': 'Remote OK|Remote Solely',
                    'hybrid': 'Hybrid',
                    'onsite': 'Onsite'
                }
                work_filter = work_map.get(work_arrangement.lower())
                print(f"Generated work arrangement filter: {work_filter}")

            # Build industry filter
            industry_filter = None
            if industries:
                industry_filter = '|'.join(industries[:3])  # Top 3 industries

            # Create primary search query if we have enough data
            if desired_titles or location_list:
                # Use normalized add_user_search_queries (creates multiple rows)
                row_count = self.cv_manager.add_user_search_queries(
                    user_id=user_id,
                    query_name='Primary Search',
                    title_keywords=desired_titles[:5] if desired_titles else None,  # List, not pipe string
                    locations=location_list if location_list else None,              # List, not pipe string
                    ai_work_arrangement=work_filter,
                    ai_seniority=seniority,
                    ai_industry=industry_filter,
                    priority=10
                )

                if row_count > 0:
                    print(f"✓ Auto-generated {row_count} search query rows for {user_email}")
                    print(f"  Titles: {desired_titles[:5] if desired_titles else ['None']}")
                    print(f"  Locations: {location_list if location_list else ['None']}")
                    print(f"  Combinations: {len(desired_titles or [1])} titles × {len(location_list or [1])} locations = {row_count} rows")
                    print(f"  Work arrangement: {work_filter or 'Any'}")
                    print(f"  Seniority: {seniority or 'Any'}")

                    # Trigger backfill for new user (1 month of jobs)
                    try:
                        from src.jobs.user_backfill import backfill_user_on_signup
                        print(f"\n🔄 Triggering 1-month backfill for {user_email}...")
                        backfill_stats = backfill_user_on_signup(
                            user_id=user_id,
                            user_email=user_email,
                            db=self.cv_manager
                        )

                        if backfill_stats.get('already_backfilled'):
                            print(f"✓ Backfill skipped - queries already backfilled by other users")
                        else:
                            print(f"✓ Backfill completed: {backfill_stats.get('new_jobs_added', 0)} jobs added")
                    except Exception as backfill_error:
                        print(f"⚠️  Warning: Backfill failed: {backfill_error}")
                        print(f"   User can still use the app, jobs will load on next daily update")
                else:
                    print(f"⚠️  Failed to create search queries for {user_email}")
            else:
                print(f"⚠️  Not enough data to auto-generate search query for {user_email}")
                print(f"    Need at least title keywords or locations from CV")

        except Exception as e:
            print(f"Warning: Could not auto-generate search queries for {user_email}: {e}")
            # Don't fail the upload if this fails


if __name__ == "__main__":
    # Test CV Handler
    print("Testing CVHandler...")

    # Note: Full test requires API key and valid CV file
    # This is a structure test only

    from src.database.cv_operations import CVManager
    from src.parsers.cv_parser import CVParser
    import os

    # Create test instances (without actual API calls)
    cv_manager = CVManager("data/test_jobs.db")
    parser = CVParser()

    # Mock analyzer (would need real API key)
    class MockAnalyzer:
        def analyze_cv(self, text, email):
            return {
                'technical_skills': ['Python', 'SQL'],
                'soft_skills': ['Leadership'],
                'languages': [{'language': 'English', 'level': 'C1'}],
                'work_experience': [],
                'total_years_experience': 5.0,
                'expertise_summary': 'Test summary',
                'parsing_cost': 0.02
            }

    analyzer = MockAnalyzer()
    handler = CVHandler(cv_manager, parser, analyzer)

    print("CVHandler structure test completed!")

    cv_manager.close()
