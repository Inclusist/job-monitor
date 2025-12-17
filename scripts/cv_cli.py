"""
CV Management CLI
Command-line interface for managing CVs
"""

import argparse
import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.cv_operations import CVManager
from src.parsers.cv_parser import CVParser
from src.analysis.cv_analyzer import CVAnalyzer
from src.cv.cv_handler import CVHandler
from dotenv import load_dotenv


def setup():
    """Initialize components"""
    # Load environment variables
    load_dotenv()

    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        sys.exit(1)

    # Initialize components
    cv_manager = CVManager("data/jobs.db")
    parser = CVParser()
    analyzer = CVAnalyzer(api_key)
    handler = CVHandler(cv_manager, parser, analyzer)

    return handler, cv_manager


def cmd_upload(args, handler):
    """Upload a new CV"""
    print("="*60)
    print("CV UPLOAD")
    print("="*60)
    print(f"User: {args.email}")
    print(f"File: {args.file}")
    print(f"Set as primary: {args.primary}")
    print()

    # Expand user path
    file_path = os.path.expanduser(args.file)

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    # Estimate cost
    file_size = os.path.getsize(file_path)
    estimated_cost = CVAnalyzer.estimate_parsing_cost(file_size)
    print(f"Estimated parsing cost: ${estimated_cost:.4f}")

    # Confirm
    if not args.yes:
        response = input("\nProceed with upload? (y/n): ")
        if response.lower() != 'y':
            print("Upload cancelled")
            return

    print("\nUploading CV...")
    result = handler.upload_cv(args.email, file_path, set_as_primary=args.primary)

    if result['success']:
        print(f"\n✓ {result['message']}")
        print(f"  CV ID: {result['cv_id']}")
        print(f"  Profile ID: {result['profile_id']}")
        print(f"  Parsing cost: ${result['parsing_cost']:.4f}")
        print(f"  Extraction status: {result['extraction_status']}")
    else:
        print(f"\n✗ {result['message']}")


def cmd_list(args, handler):
    """List all CVs for a user"""
    cvs = handler.get_user_cvs(args.email)

    if not cvs:
        print(f"No CVs found for {args.email}")
        return

    print("="*60)
    print(f"CVs FOR {args.email}")
    print("="*60)

    for cv in cvs:
        primary = "★ PRIMARY" if cv['is_primary'] else ""
        print(f"\nCV ID: {cv['id']} {primary}")
        print(f"  File: {cv['file_name']}")
        print(f"  Type: {cv['file_type'].upper()}")
        print(f"  Size: {cv['file_size'] / 1024:.1f} KB")
        print(f"  Uploaded: {cv['uploaded_date'][:10]}")
        print(f"  Version: {cv['version']}")
        print(f"  Status: {cv['status']}")


def cmd_show_profile(args, handler, cv_manager):
    """Show extracted CV profile"""
    cv = handler.get_primary_cv(args.email)

    if not cv:
        print(f"No primary CV found for {args.email}")
        return

    profile = cv.get('profile')
    if not profile:
        print("No profile data found")
        return

    print("="*60)
    print(f"CV PROFILE FOR {args.email}")
    print("="*60)
    print(f"\nCV: {cv['file_name']}")
    print(f"Uploaded: {cv['uploaded_date'][:10]}")
    print()

    print("EXPERTISE SUMMARY:")
    print(profile.get('expertise_summary', 'N/A'))
    print()

    print(f"TOTAL EXPERIENCE: {profile.get('total_years_experience', 0)} years")
    print()

    print("TECHNICAL SKILLS:")
    skills = profile.get('technical_skills', [])
    if skills:
        print(", ".join(skills[:20]))  # Show first 20
        if len(skills) > 20:
            print(f"  ... and {len(skills) - 20} more")
    else:
        print("  None listed")
    print()

    print("LANGUAGES:")
    languages = profile.get('languages', [])
    if languages:
        for lang in languages:
            if isinstance(lang, dict):
                print(f"  - {lang.get('language')}: {lang.get('level', 'N/A')}")
            else:
                print(f"  - {lang}")
    else:
        print("  None listed")
    print()

    print("WORK EXPERIENCE:")
    experience = profile.get('work_experience', [])
    if experience:
        for i, job in enumerate(experience[:5], 1):  # Show first 5
            print(f"  {i}. {job.get('title')} at {job.get('company')}")
            print(f"     Duration: {job.get('duration', 'N/A')}")
    else:
        print("  None listed")
    if len(experience) > 5:
        print(f"  ... and {len(experience) - 5} more positions")
    print()

    print("EDUCATION:")
    education = profile.get('education', [])
    if education:
        for edu in education:
            print(f"  - {edu.get('degree')} from {edu.get('institution')} ({edu.get('year', 'N/A')})")
    else:
        print("  None listed")
    print()

    if args.full:
        print("\nFULL PROFILE DATA:")
        print(json.dumps({k: v for k, v in profile.items() if k != 'full_text'}, indent=2))


def cmd_set_primary(args, handler):
    """Set a CV as primary"""
    result = handler.switch_primary_cv(args.email, args.cv_id)

    if result['success']:
        print(f"✓ {result['message']}")
    else:
        print(f"✗ {result['message']}")


def cmd_delete(args, handler):
    """Delete a CV"""
    # Confirm deletion
    if not args.yes:
        response = input(f"Delete CV {args.cv_id}? This cannot be undone. (y/n): ")
        if response.lower() != 'y':
            print("Deletion cancelled")
            return

    result = handler.delete_cv(args.email, args.cv_id, delete_files=not args.keep_files)

    if result['success']:
        print(f"✓ {result['message']}")
    else:
        print(f"✗ {result['message']}")


def cmd_reparse(args, handler):
    """Reparse a CV with updated prompt"""
    print(f"Reparsing CV {args.cv_id}...")

    # Estimate cost
    estimated_cost = 0.02  # Typical cost
    print(f"Estimated parsing cost: ${estimated_cost:.4f}")

    # Confirm
    if not args.yes:
        response = input("\nProceed with reparsing? (y/n): ")
        if response.lower() != 'y':
            print("Reparsing cancelled")
            return

    result = handler.reparse_cv(args.cv_id)

    if result['success']:
        print(f"\n✓ {result['message']}")
        print(f"  Parsing cost: ${result['parsing_cost']:.4f}")
    else:
        print(f"\n✗ {result['message']}")


def cmd_stats(args, handler):
    """Show CV statistics"""
    if args.email:
        stats = handler.get_cv_statistics(args.email)
        print("="*60)
        print(f"CV STATISTICS FOR {args.email}")
        print("="*60)
    else:
        stats = handler.get_cv_statistics()
        print("="*60)
        print("GLOBAL CV STATISTICS")
        print("="*60)

    if 'error' in stats:
        print(f"Error: {stats['error']}")
        return

    for key, value in stats.items():
        formatted_key = key.replace('_', ' ').title()
        print(f"{formatted_key}: {value}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='CV Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload a CV
  python scripts/cv_cli.py upload --email user@example.com --file ~/cv.pdf --primary

  # List all CVs
  python scripts/cv_cli.py list --email user@example.com

  # Show extracted profile
  python scripts/cv_cli.py show-profile --email user@example.com

  # Set a different CV as primary
  python scripts/cv_cli.py set-primary --email user@example.com --cv-id 3

  # Delete a CV
  python scripts/cv_cli.py delete --email user@example.com --cv-id 2

  # Reparse CV with updated prompt
  python scripts/cv_cli.py reparse --cv-id 3

  # Show statistics
  python scripts/cv_cli.py stats
  python scripts/cv_cli.py stats --email user@example.com
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a new CV')
    upload_parser.add_argument('--email', required=True, help='User email')
    upload_parser.add_argument('--file', required=True, help='Path to CV file')
    upload_parser.add_argument('--primary', action='store_true',
                               help='Set as primary CV (default: yes)', default=True)
    upload_parser.add_argument('--no-primary', dest='primary', action='store_false',
                               help='Do not set as primary CV')
    upload_parser.add_argument('-y', '--yes', action='store_true',
                               help='Skip confirmation prompt')

    # List command
    list_parser = subparsers.add_parser('list', help='List all CVs for a user')
    list_parser.add_argument('--email', required=True, help='User email')

    # Show profile command
    profile_parser = subparsers.add_parser('show-profile', help='Show extracted CV profile')
    profile_parser.add_argument('--email', required=True, help='User email')
    profile_parser.add_argument('--full', action='store_true',
                                help='Show full profile JSON')

    # Set primary command
    primary_parser = subparsers.add_parser('set-primary', help='Set a CV as primary')
    primary_parser.add_argument('--email', required=True, help='User email')
    primary_parser.add_argument('--cv-id', type=int, required=True, help='CV ID')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a CV')
    delete_parser.add_argument('--email', required=True, help='User email')
    delete_parser.add_argument('--cv-id', type=int, required=True, help='CV ID')
    delete_parser.add_argument('--keep-files', action='store_true',
                               help='Keep files on disk (only delete from database)')
    delete_parser.add_argument('-y', '--yes', action='store_true',
                               help='Skip confirmation prompt')

    # Reparse command
    reparse_parser = subparsers.add_parser('reparse', help='Reparse a CV with updated prompt')
    reparse_parser.add_argument('--cv-id', type=int, required=True, help='CV ID')
    reparse_parser.add_argument('-y', '--yes', action='store_true',
                                help='Skip confirmation prompt')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show CV statistics')
    stats_parser.add_argument('--email', help='User email (optional - shows global stats if omitted)')

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Change to project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    # Initialize components
    try:
        handler, cv_manager = setup()
    except Exception as e:
        print(f"Error initializing: {e}")
        sys.exit(1)

    # Execute command
    try:
        if args.command == 'upload':
            cmd_upload(args, handler)
        elif args.command == 'list':
            cmd_list(args, handler)
        elif args.command == 'show-profile':
            cmd_show_profile(args, handler, cv_manager)
        elif args.command == 'set-primary':
            cmd_set_primary(args, handler)
        elif args.command == 'delete':
            cmd_delete(args, handler)
        elif args.command == 'reparse':
            cmd_reparse(args, handler)
        elif args.command == 'stats':
            cmd_stats(args, handler)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cv_manager.close()


if __name__ == "__main__":
    main()
