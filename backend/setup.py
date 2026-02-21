#!/usr/bin/env python3
"""
Setup script for Inclusist
Helps configure the system and test connections
"""

import os
import sys
from dotenv import load_dotenv


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(text)
    print("="*60 + "\n")


def check_env_file():
    """Check if .env file exists"""
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("\nCreating .env from template...")
        
        if os.path.exists('.env.template'):
            import shutil
            shutil.copy('.env.template', '.env')
            print("✅ Created .env file")
            print("\n⚠️  Please edit .env and add your API keys:")
            print("   - INDEED_PUBLISHER_ID (get from https://www.indeed.com/publisher)")
            print("   - ANTHROPIC_API_KEY (get from https://console.anthropic.com/)")
            return False
        else:
            print("❌ .env.template not found!")
            return False
    else:
        print("✅ .env file found")
        return True


def check_api_keys():
    """Check if API keys are configured"""
    load_dotenv()
    
    keys_ok = True
    
    # Check Indeed
    indeed_key = os.getenv('INDEED_PUBLISHER_ID')
    if not indeed_key or indeed_key == 'your_publisher_id_here':
        print("❌ INDEED_PUBLISHER_ID not configured")
        print("   Get it from: https://www.indeed.com/publisher")
        keys_ok = False
    else:
        print(f"✅ Indeed Publisher ID configured: {indeed_key[:10]}...")
    
    # Check Anthropic
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_key or anthropic_key == 'your_claude_api_key_here':
        print("❌ ANTHROPIC_API_KEY not configured")
        print("   Get it from: https://console.anthropic.com/")
        keys_ok = False
    else:
        print(f"✅ Anthropic API key configured: {anthropic_key[:20]}...")
    
    return keys_ok


def test_database():
    """Test database creation"""
    try:
        sys.path.insert(0, 'src')
        from database.operations import JobDatabase
        
        db = JobDatabase("data/jobs.db")
        stats = db.get_statistics()
        db.close()
        
        print(f"✅ Database working (contains {stats['total_jobs']} jobs)")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_indeed():
    """Test Indeed API connection"""
    try:
        load_dotenv()
        publisher_id = os.getenv('INDEED_PUBLISHER_ID')
        
        if not publisher_id or publisher_id == 'your_publisher_id_here':
            print("❌ Cannot test Indeed - API key not configured")
            return False
        
        sys.path.insert(0, 'src')
        from collectors.indeed import IndeedCollector
        
        collector = IndeedCollector(publisher_id)
        jobs = collector.search("Data Scientist", "Germany", limit=3, days_back=7)
        
        if jobs:
            print(f"✅ Indeed API working ({len(jobs)} test jobs found)")
            print(f"   Example: {jobs[0]['title']} at {jobs[0]['company']}")
            return True
        else:
            print("⚠️  Indeed API working but no jobs found (try different search terms)")
            return True
            
    except Exception as e:
        print(f"❌ Indeed API error: {e}")
        return False


def test_claude():
    """Test Claude API connection"""
    try:
        load_dotenv()
        import yaml
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == 'your_claude_api_key_here':
            print("❌ Cannot test Claude - API key not configured")
            return False
        
        sys.path.insert(0, 'src')
        from analysis.claude_analyzer import ClaudeJobAnalyzer
        
        # Load config
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        analyzer = ClaudeJobAnalyzer(api_key, model="claude-haiku-4-5-20251001")
        analyzer.set_profile(config['profile'])
        
        # Test with a simple job
        test_job = {
            'title': 'Senior Data Scientist',
            'company': 'Test Company',
            'location': 'Berlin, Germany',
            'description': 'Looking for data scientist with Python and ML experience'
        }
        
        analysis = analyzer.analyze_job(test_job)
        
        if analysis and 'match_score' in analysis:
            print(f"✅ Claude API working (test score: {analysis['match_score']})")
            return True
        else:
            print("❌ Claude API returned unexpected response")
            return False
            
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        return False


def main():
    """Main setup function"""
    print_header("Inclusist - Setup & Test")

    print("This script will help you set up and test Inclusist.\n")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher required")
        print(f"   Current version: {sys.version}")
        return
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")
    
    # Check dependencies
    try:
        import requests
        import anthropic
        import yaml
        print("✅ Required packages installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("\nPlease run: pip install -r requirements.txt")
        return
    
    print_header("1. Checking Configuration Files")
    
    # Check .env
    env_ok = check_env_file()
    
    if not env_ok:
        print("\n⚠️  Please configure .env file and run this script again")
        return
    
    print_header("2. Checking API Keys")
    
    keys_ok = check_api_keys()
    
    if not keys_ok:
        print("\n⚠️  Please add your API keys to .env file and run this script again")
        return
    
    print_header("3. Testing Components")
    
    # Test database
    print("\nTesting database...")
    db_ok = test_database()
    
    # Test Indeed
    print("\nTesting Indeed API...")
    indeed_ok = test_indeed()
    
    # Test Claude
    print("\nTesting Claude API...")
    claude_ok = test_claude()
    
    print_header("Setup Summary")
    
    if db_ok and indeed_ok and claude_ok:
        print("✅ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Review and customize config.yaml")
        print("2. Run: python main.py")
        print("3. Check logs in data/logs/job_monitor.log")
    else:
        print("⚠️  Some tests failed. Please fix the issues above and try again.")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
