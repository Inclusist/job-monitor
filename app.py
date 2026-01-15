#!/usr/bin/env python3
"""
Flask Web Application for Job Monitor
Simple web UI for CV management and job viewing
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import json
import time
import queue
import threading
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.factory import get_database
from database.cv_operations import CVManager
from parsers.cv_parser import CVParser
from analysis.cv_analyzer import CVAnalyzer
from analysis.search_suggester import SearchSuggester
from analysis.cover_letter_generator import CoverLetterGenerator
from cv.cv_handler import CVHandler
from collectors.adzuna import AdzunaCollector
from collectors.activejobs import ActiveJobsCollector
from utils.job_loader import trigger_new_user_job_load, trigger_preferences_update_job_load, get_default_preferences

# Load environment variables
load_dotenv()

# Import filter and analysis functions
import importlib.util
filter_spec = importlib.util.spec_from_file_location("filter_jobs", "scripts/filter_jobs.py")
filter_module = importlib.util.module_from_spec(filter_spec)
filter_spec.loader.exec_module(filter_module)

# Initialize Flask app
app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Fix for HTTPS behind proxy (Railway, etc.)
# This ensures OAuth redirect URIs use HTTPS instead of HTTP
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Configuration
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize components
db_path = os.getenv('DATABASE_PATH', 'data/jobs.db')
job_db = get_database()  # Auto-detects SQLite or PostgreSQL based on DATABASE_URL

# Initialize CV Manager - use PostgreSQL if DATABASE_URL is set, otherwise SQLite
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres'):
    from src.database.postgres_cv_operations import PostgresCVManager
    # Reuse the connection pool from job_db if it's PostgreSQL
    if hasattr(job_db, 'connection_pool'):
        cv_manager = PostgresCVManager(job_db.connection_pool)
        print("✓ Using PostgreSQL for user/CV operations")
    else:
        # Fallback to SQLite if job_db is not PostgreSQL
        cv_manager = CVManager(db_path)
        print("✓ Using SQLite for user/CV operations")
else:
    cv_manager = CVManager(db_path)
    print("✓ Using SQLite for user/CV operations")

parser = CVParser()

# Initialize CV analyzer
anthropic_key = os.getenv('ANTHROPIC_API_KEY')
if not anthropic_key:
    print("Warning: ANTHROPIC_API_KEY not set. CV upload will not work.")
    analyzer = None
else:
    analyzer = CVAnalyzer(anthropic_key)

handler = CVHandler(cv_manager, parser, analyzer, storage_root='data/cvs') if analyzer else None

# Initialize Resume Generator and Operations
resume_ops = None
resume_generator = None
if database_url and database_url.startswith('postgres') and hasattr(job_db, 'connection_pool'):
    from src.database.postgres_resume_operations import PostgresResumeOperations
    from src.resume.resume_generator import ResumeGenerator

    resume_ops = PostgresResumeOperations(job_db.connection_pool)

    if anthropic_key:
        resume_generator = ResumeGenerator(anthropic_key)
        print("✓ Resume generation enabled")
    else:
        print("Warning: Resume generation disabled (ANTHROPIC_API_KEY not set)")
else:
    print("Warning: Resume generation disabled (PostgreSQL required)")

# Progress tracking for job search
search_progress = {}

# Semantic search models (lazy loading)
_semantic_models = {}

def get_semantic_model(model_name='TechWolf/JobBERT-v3'):
    """Get or load sentence transformer model (lazy loading with caching)

    Supported models:
    - TechWolf/JobBERT-v3: Job-specialized semantic matching (EN, DE, ES, CN) [DEFAULT]
    - paraphrase-multilingual-MiniLM-L12-v2: General multilingual (50+ languages)
    """
    global _semantic_models

    if model_name not in _semantic_models:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            print(f"📥 Loading sentence transformer model: {model_name}...")

            # Fix for PyTorch 2.9+ compatibility with meta tensors
            # Use device_map and trust_remote_code for TechWolf models
            if 'TechWolf' in model_name or 'JobBERT' in model_name:
                _semantic_models[model_name] = SentenceTransformer(
                    model_name,
                    device='cpu',  # Explicitly set device
                    trust_remote_code=True
                )
            else:
                # Also use explicit device for other models for consistency
                _semantic_models[model_name] = SentenceTransformer(model_name, device='cpu')

            print(f"✅ Model loaded: {model_name}")
        except ImportError:
            print("❌ Error: sentence-transformers package not installed")
            return None
        except Exception as e:
            print(f"❌ Error loading model {model_name}: {e}")
            return None

    return _semantic_models[model_name]

# Initialize OAuth
oauth = OAuth(app)

# Configure Google OAuth
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Configure LinkedIn OAuth (OpenID Connect without nonce)
# Note: LinkedIn's OIDC implementation doesn't include nonce in ID token
linkedin = oauth.register(
    name='linkedin',
    client_id=os.getenv('LINKEDIN_CLIENT_ID'),
    client_secret=os.getenv('LINKEDIN_CLIENT_SECRET'),
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    userinfo_endpoint='https://api.linkedin.com/v2/userinfo',
    jwks_uri='https://www.linkedin.com/oauth/openid/jwks',
    client_kwargs={
        'scope': 'openid profile email',
        'token_endpoint_auth_method': 'client_secret_post',
    }
)


# ============ Flask-Login User Class ============

class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.email = user_dict['email']
        self.name = user_dict.get('name')
        self.provider = user_dict.get('provider', 'email')  # 'google', 'linkedin', or 'email'
        self.avatar_url = user_dict.get('avatar_url')  # Profile picture from OAuth
        self._is_active = bool(user_dict.get('is_active', 1))
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_active(self):
        """Override UserMixin's is_active property"""
        return self._is_active


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    user_dict = cv_manager.get_user_by_id(int(user_id))
    if user_dict:
        return User(user_dict)
    return None


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_email():
    """Get user email from current_user or fallback"""
    if current_user.is_authenticated:
        return current_user.email
    return os.getenv('USER_EMAIL') or 'default@localhost'


def get_user_id():
    """Get user ID from current_user or fallback"""
    if current_user.is_authenticated:
        return current_user.id
    # Fallback for development
    email = os.getenv('USER_EMAIL') or 'default@localhost'
    user = cv_manager.get_or_create_user(email=email)
    return user['id']


def get_user_context():
    """Get user and CV statistics"""
    email = get_user_email()
    user = cv_manager.get_or_create_user(email=email)

    # Get statistics
    user_stats = cv_manager.get_user_statistics(user['id'])

    # Get job statistics
    job_stats = job_db.get_statistics()

    # Combine stats
    stats = {
        'total_cvs': user_stats.get('cv_count', 0),  # Fixed: was total_cvs, should be cv_count
        'primary_cv_name': user_stats.get('primary_cv_name'),
        'total_jobs': job_stats.get('total_jobs', 0),
        'high_priority': job_stats.get('by_priority', {}).get('high', 0)
    }

    return user, stats


# ============ Authentication Routes ============

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        
        # Validation
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        # Register user
        user_id = cv_manager.register_user(email, password, name)

        if user_id:
            flash('Registration successful! Please log in.', 'success')

            # Trigger automatic job loading for new user with default preferences
            try:
                defaults = get_default_preferences()
                if defaults['keywords'] and defaults['locations']:
                    trigger_new_user_job_load(
                        user_id=user_id,
                        keywords=defaults['keywords'],
                        locations=defaults['locations'],
                        job_db=job_db,
                        cv_manager=cv_manager
                    )
                    flash('Loading initial jobs in the background...', 'info')
            except Exception as e:
                print(f"Error triggering job load for new user: {e}")

            return redirect(url_for('login'))
        else:
            flash('Email already registered', 'error')
            return render_template('register.html')
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        # Authenticate user
        user_dict = cv_manager.authenticate_user(email, password)
        
        if user_dict:
            user = User(user_dict)
            login_user(user, remember=remember)
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
            return render_template('login.html')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))


# ============ OAuth Routes ============

@app.route('/login/google')
def login_google():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/authorize/google')
def authorize_google():
    """Google OAuth callback"""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user information from Google', 'error')
            return redirect(url_for('login'))
        
        email = user_info.get('email')
        name = user_info.get('name')
        avatar_url = user_info.get('picture')
        
        if not email:
            flash('Email not provided by Google', 'error')
            return redirect(url_for('login'))
        
        # Get or create user with OAuth provider info
        user_dict = cv_manager.get_or_create_oauth_user(
            email=email,
            name=name,
            provider='google',
            avatar_url=avatar_url
        )
        
        print(f"Google OAuth - user_dict result: {user_dict}")
        
        if user_dict:
            user = User(user_dict)
            login_user(user, remember=True)
            
            # Check if this is a new user
            is_new_user = user_dict.get('is_new_user', False)
            if is_new_user:
                flash(f'Welcome {name}! Your account has been created.', 'success')
                
                # Trigger automatic job loading for new user
                try:
                    defaults = get_default_preferences()
                    if defaults['keywords'] and defaults['locations']:
                        trigger_new_user_job_load(
                            user_id=user.id,
                            keywords=defaults['keywords'],
                            locations=defaults['locations'],
                            job_db=job_db,
                            cv_manager=cv_manager
                        )
                        flash('Loading initial jobs in the background...', 'info')
                except Exception as e:
                    print(f"Error triggering job load for new user: {e}")
            else:
                flash(f'Welcome back, {name}!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Failed to create user account', 'error')
            return redirect(url_for('login'))
            
    except Exception as e:
        import traceback
        print(f"Google OAuth error: {e}")
        print(traceback.format_exc())
        flash(f'Failed to authenticate with Google: {str(e)}', 'error')
        return redirect(url_for('login'))


@app.route('/login/linkedin')
def login_linkedin():
    """Initiate LinkedIn OAuth login"""
    redirect_uri = url_for('authorize_linkedin', _external=True)
    # Note: LinkedIn doesn't support nonce in ID token, so we don't send it
    # The state parameter still provides CSRF protection
    return linkedin.authorize_redirect(redirect_uri)


@app.route('/authorize/linkedin')
def authorize_linkedin():
    """LinkedIn OAuth callback"""
    try:
        # Manually exchange authorization code for access token to bypass ID token validation
        # LinkedIn's OIDC implementation doesn't include nonce, which breaks authlib's validation
        import requests

        code = request.args.get('code')
        if not code:
            flash('Authorization failed: No code received', 'error')
            return redirect(url_for('login'))

        # Exchange code for access token
        token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        redirect_uri = url_for('authorize_linkedin', _external=True)

        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': os.getenv('LINKEDIN_CLIENT_ID'),
            'client_secret': os.getenv('LINKEDIN_CLIENT_SECRET'),
        }

        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            raise Exception(f"Token exchange failed: {token_response.text}")

        token = token_response.json()
        access_token = token.get('access_token')

        if not access_token:
            raise Exception("No access token received")

        # Fetch user info from LinkedIn's userinfo endpoint
        userinfo_url = 'https://api.linkedin.com/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)

        if userinfo_response.status_code != 200:
            raise Exception(f"UserInfo request failed: {userinfo_response.text}")

        user_info = userinfo_response.json()
        
        # Debug print
        print("LinkedIn userinfo response:", user_info)
        
        email = user_info.get('email')
        name = user_info.get('name')
        avatar_url = user_info.get('picture')
        
        if not email:
            print("Available fields in LinkedIn response:", list(user_info.keys()))
            flash('Email not provided by LinkedIn', 'error')
            return redirect(url_for('login'))
        
        # Get or create user with OAuth provider info
        user_dict = cv_manager.get_or_create_oauth_user(
            email=email,
            name=name,
            provider='linkedin',
            avatar_url=avatar_url
        )
        
        if user_dict:
            user = User(user_dict)
            login_user(user, remember=True)
            
            # Check if this is a new user
            is_new_user = user_dict.get('is_new_user', False)
            if is_new_user:
                flash(f'Welcome {name}! Your account has been created.', 'success')
                
                # Trigger automatic job loading for new user
                try:
                    defaults = get_default_preferences()
                    if defaults['keywords'] and defaults['locations']:
                        trigger_new_user_job_load(
                            user_id=user.id,
                            keywords=defaults['keywords'],
                            locations=defaults['locations'],
                            job_db=job_db,
                            cv_manager=cv_manager
                        )
                        flash('Loading initial jobs in the background...', 'info')
                except Exception as e:
                    print(f"Error triggering job load for new user: {e}")
            else:
                flash(f'Welcome back, {name}!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Failed to create user account', 'error')
            return redirect(url_for('login'))
            
    except Exception as e:
        import traceback
        print(f"LinkedIn OAuth error: {e}")
        print(traceback.format_exc())
        flash(f'Failed to authenticate with LinkedIn: {str(e)}', 'error')
        return redirect(url_for('login'))


# ============ Main Routes ============

@app.route('/')
@login_required
def index():
    """Home page"""
    user, stats = get_user_context()
    return render_template('index.html', user=user, stats=stats)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_cv():
    """CV upload page"""
    if request.method == 'POST':
        if not handler:
            flash('CV upload is not available. ANTHROPIC_API_KEY not configured.', 'error')
            return redirect(url_for('upload_cv'))

        # Get form data
        email = request.form.get('email')
        set_primary = request.form.get('set_primary') == 'on'

        if not email:
            flash('Email is required', 'error')
            return redirect(url_for('upload_cv'))

        # Check if file was uploaded
        if 'cv_file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('upload_cv'))

        file = request.files['cv_file']

        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('upload_cv'))

        if not allowed_file(file.filename):
            flash('Invalid file type. Only PDF, DOCX, and TXT are allowed.', 'error')
            return redirect(url_for('upload_cv'))

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)

        try:
            # Upload CV
            result = handler.upload_cv(email, temp_path, set_as_primary=set_primary)

            if result['success']:
                flash(f"✓ {result['message']} (Cost: ${result['parsing_cost']:.4f})", 'success')
                session['user_email'] = email  # Save email to session

                # Clean up temp file
                os.remove(temp_path)

                return redirect(url_for('view_profile'))
            else:
                flash(f"✗ {result['message']}", 'error')
                os.remove(temp_path)
                return redirect(url_for('upload_cv'))

        except Exception as e:
            flash(f'Error uploading CV: {str(e)}', 'error')
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return redirect(url_for('upload_cv'))

    # GET request
    email = get_user_email()
    return render_template('upload.html', email=email)


@app.route('/profile')
@login_required
def view_profile():
    """View CV profile"""
    user, stats = get_user_context()

    # Get all CVs for the user
    all_cvs = cv_manager.get_user_cvs(user['id'])
    
    # Get primary CV and profile
    cv = cv_manager.get_primary_cv(user['id'])

    if not cv:
        # Check if user has any CVs at all (not just primary)
        if all_cvs:
            # User has CVs but none marked as primary - use the most recent one
            cv = all_cvs[0]
            flash(f"Showing most recent CV: {cv['file_name']}. Click 'Set as Primary' to make it your default.", 'info')
        else:
            return render_template('profile.html', user=user, profile=None, cv=None, all_cvs=[])

    profile = cv_manager.get_cv_profile(cv['id'])
    
    if not profile:
        flash(f"CV uploaded but profile not parsed. Please try uploading again.", 'warning')

    print(f"DEBUG: Viewing Profile for User {user['id']}")
    if cv:
        print(f"DEBUG: CV ID: {cv['id']} (File: {cv['file_name']})")
    
    if profile:
        print(f"DEBUG: Profile ID: {profile.get('id')}")
        comps = profile.get('competencies')
        print(f"DEBUG: Competencies Type: {type(comps)}")
        print(f"DEBUG: Competencies Value: {comps}")

    # Parse JSON fields
    if profile:
        json_fields = ['technical_skills', 'soft_skills', 'competencies', 'languages', 'certifications',
                      'work_experience', 'leadership_experience', 'education',
                      'career_highlights', 'industries', 'raw_analysis']

        for field in json_fields:
            if field in profile and isinstance(profile[field], str):
                try:
                    profile[field] = json.loads(profile[field])
                except:
                    profile[field] = []
        
        # DEBUG after parsing
        print(f"DEBUG: Post-Parsing Competencies: {profile.get('competencies')}")

    # Get user-claimed competencies/skills for resume generation
    claimed_data = None
    if resume_ops:
        try:
            claimed_data = resume_ops.get_user_claimed_data(user['id'])
        except Exception as e:
            print(f"Warning: Could not fetch claimed data: {e}")

    return render_template('profile.html', user=user, profile=profile, cv=cv, all_cvs=all_cvs, claimed_data=claimed_data)


@app.route('/delete-cv/<int:cv_id>', methods=['POST'])
@login_required
def delete_cv(cv_id):
    """Delete a CV"""
    try:
        email = get_user_email()
        user = cv_manager.get_or_create_user(email=email)
        
        # Verify CV belongs to user
        cv = cv_manager.get_cv(cv_id)
        if not cv or cv['user_id'] != user['id']:
            flash('CV not found or access denied', 'error')
            return redirect(url_for('view_profile'))
        
        # Delete CV (hard delete - removes CV and profile)
        cv_manager.delete_cv(cv_id)
        
        # Also delete the physical file if it exists
        if handler and cv.get('file_path'):
            file_path = os.path.join('data/cvs', cv['file_path'])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        flash(f"✓ CV '{cv['file_name']}' deleted successfully", 'success')
        return redirect(url_for('view_profile'))
        
    except Exception as e:
        flash(f'Error deleting CV: {str(e)}', 'error')
        return redirect(url_for('view_profile'))


@app.route('/set-primary-cv/<int:cv_id>', methods=['POST'])
@login_required
def set_primary_cv(cv_id):
    """Set a CV as primary"""
    try:
        email = get_user_email()
        user = cv_manager.get_or_create_user(email=email)
        
        # Set as primary
        cv_manager.set_primary_cv(user['id'], cv_id)
        
        flash('✓ Primary CV updated', 'success')
        return redirect(url_for('view_profile'))
        
    except Exception as e:
        flash(f'Error setting primary CV: {str(e)}', 'error')
        return redirect(url_for('view_profile'))


@app.route('/jobs')
@login_required
def jobs():
    """Jobs dashboard"""
    user, stats = get_user_context()
    
    print(f"DEBUG: Current user email: {user.get('email')}, user_id: {user.get('id')}")

    # Get filter parameters
    priority = request.args.get('priority', '')
    status = request.args.get('status', '')
    min_score = request.args.get('min_score', type=int, default=0)  # Show all matches by default

    # Get jobs for user from user_job_matches
    try:
        # Query user_job_matches - show semantic matches too
        matches = job_db.get_user_job_matches(
            user_id=user['id'],
            min_semantic_score=min_score if min_score else 0,
            limit=1000
        )
        
        print(f"DEBUG: Retrieved {len(matches)} matches for user {user['id']}")
        if matches:
            print(f"DEBUG: First match keys: {list(matches[0].keys())}")
            print(f"DEBUG: First match sample: job_id={matches[0].get('job_id')}, title={matches[0].get('title')}, discovered_date={matches[0].get('discovered_date')}")
        else:
            print(f"DEBUG: No matches found. Checking database directly...")
            # Quick direct check
            import psycopg2
            from psycopg2.extras import RealDictCursor
            import os
            db_url = os.getenv('DATABASE_URL')
            if db_url:
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('SELECT COUNT(*) as count FROM user_job_matches WHERE user_id = %s', (user['id'],))
                count = cursor.fetchone()['count']
                print(f"DEBUG: Direct DB query shows {count} matches for user_id {user['id']}")
                cursor.close()
                conn.close()
        
        # Filter by priority if specified
        if priority:
            matches = [m for m in matches if m.get('priority') == priority]
        
        # Filter by status if specified
        if status:
            matches = [m for m in matches if m.get('status') == status]
        
        # Separate by discovery date (new vs previous)
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        new_jobs = []
        previous_jobs = []
        
        for match in matches:
            # Use claude_score as the primary match_score for display
            if match.get('claude_score'):
                match['match_score'] = match['claude_score']
            elif match.get('semantic_score'):
                match['match_score'] = match['semantic_score']
            else:
                match['match_score'] = None
            
            # Check discovery date
            discovered = match.get('discovered_date')
            if discovered:
                # Handle both string (SQLite) and datetime (PostgreSQL) formats
                if isinstance(discovered, str):
                    try:
                        discovered_date = datetime.fromisoformat(discovered.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        discovered_date = None
                elif hasattr(discovered, 'date'):
                    # It's already a datetime object (PostgreSQL)
                    discovered_date = discovered.date()
                else:
                    # It's already a date object
                    discovered_date = discovered
                
                if discovered_date and discovered_date == today:
                    new_jobs.append(match)
                else:
                    previous_jobs.append(match)
            else:
                previous_jobs.append(match)

        # Parse JSON fields for both lists
        for job in new_jobs + previous_jobs:
            # Map job_location to location for template
            if 'job_location' in job:
                job['location'] = job['job_location']
            
            # Debug: print first job's location
            if job == (new_jobs + previous_jobs)[0]:
                print(f"DEBUG: First job job_id: {job.get('job_id')}, job_table_id: {job.get('job_table_id')}")
                print(f"DEBUG: First job title: {job.get('title')[:50]}")
                print(f"DEBUG: First job location: {repr(job.get('location'))}")
                print(f"DEBUG: First job job_location: {repr(job.get('job_location'))}")
            
            if job.get('key_alignments') and isinstance(job['key_alignments'], str):
                try:
                    job['key_alignments'] = json.loads(job['key_alignments'])
                except:
                    job['key_alignments'] = []

            if job.get('potential_gaps') and isinstance(job['potential_gaps'], str):
                try:
                    job['potential_gaps'] = json.loads(job['potential_gaps'])
                except:
                    job['potential_gaps'] = []
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        import traceback
        traceback.print_exc()
        new_jobs = []
        previous_jobs = []
        flash('No jobs found. Run filter_jobs.py to analyze jobs.', 'info')

    return render_template('jobs.html', user=user, stats=stats,
                          new_jobs=new_jobs, previous_jobs=previous_jobs,
                          priority=priority, min_score=min_score, status=status)


@app.route('/semantic-search')
@login_required
def semantic_search():
    """Semantic search testing page"""
    user, stats = get_user_context()

    # Check if user has a CV profile
    cv_profile = cv_manager.get_profile_by_user(user['id'])

    if not cv_profile:
        flash('Please upload your CV first to use semantic search', 'warning')
        return redirect(url_for('upload_cv'))

    # Get job count
    conn = job_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    job_count = cursor.fetchone()[0]
    cursor.close()
    if hasattr(job_db, '_return_connection'):
        job_db._return_connection(conn)
    else:
        conn.close()

    return render_template('semantic_search.html', user=user, stats=stats, job_count=job_count)


@app.route('/run-semantic-search', methods=['POST'])
@login_required
def run_semantic_search():
    """Run semantic search and return results"""
    user, stats = get_user_context()

    try:
        # Get parameters
        query = request.json.get('query', '').strip()
        threshold = float(request.json.get('threshold', 0.5))
        match_mode = request.json.get('match_mode', 'title_only')  # title_only or full_text
        limit = int(request.json.get('limit', 20))
        locations = request.json.get('locations', [])
        include_remote = request.json.get('include_remote', True)
        model_name = request.json.get('model', 'TechWolf/JobBERT-v3')

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Load model
        model = get_semantic_model(model_name)
        if model is None:
            return jsonify({'error': f'Failed to load model: {model_name}'}), 500

        # Get jobs with optional location filtering
        start_time = time.time()
        conn = job_db._get_connection()

        # Use RealDictCursor for PostgreSQL
        try:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        except ImportError:
            # SQLite fallback
            cursor = conn.cursor()
            cursor.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))

        # Build query with optional location filter (include pre-computed embeddings)
        query_sql = """
            SELECT id, title, company, location, description,
                   discovered_date, url, ai_work_arrangement,
                   cities_derived, locations_derived, embedding_jobbert_title
            FROM jobs
        """
        params = []

        # Apply location filter if specified
        if locations or include_remote:
            conditions = []

            if include_remote:
                # Use parameter to avoid % escaping issues
                conditions.append("ai_work_arrangement ILIKE %s")
                params.append('%remote%')

            if locations and len(locations) > 0:
                # Build ILIKE patterns for each location
                location_patterns = [f'%{loc}%' for loc in locations]
                conditions.append("""
                    (EXISTS (
                        SELECT 1 FROM unnest(cities_derived) AS city
                        WHERE city ILIKE ANY(%s)
                    )
                    OR
                    EXISTS (
                        SELECT 1 FROM unnest(locations_derived) AS loc
                        WHERE loc ILIKE ANY(%s)
                    ))
                """)
                params.extend([location_patterns, location_patterns])

            if len(conditions) > 0:
                query_sql += " WHERE (" + " OR ".join(conditions) + ")"

        query_sql += " ORDER BY discovered_date DESC"

        cursor.execute(query_sql, params)
        jobs = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        if hasattr(job_db, '_return_connection'):
            job_db._return_connection(conn)
        else:
            conn.close()

        fetch_time = time.time() - start_time

        # Encode query
        encode_start = time.time()
        query_embedding = model.encode(query, show_progress_bar=False)
        query_encode_time = time.time() - encode_start

        # Load pre-computed embeddings (80-100x faster!)
        load_start = time.time()
        job_embeddings = {}
        jobs_needing_encoding = []

        for job in jobs:
            # For title_only mode, use pre-computed embeddings
            if match_mode == 'title_only' and job.get('embedding_jobbert_title'):
                try:
                    import json
                    embedding_json = job['embedding_jobbert_title']
                    if isinstance(embedding_json, str):
                        embedding_data = json.loads(embedding_json)
                    else:
                        embedding_data = embedding_json
                    job_embeddings[job['id']] = np.array(embedding_data)
                except Exception as e:
                    print(f"⚠️  Failed to load embedding for job {job['id']}: {e}")
                    jobs_needing_encoding.append(job)
            else:
                # Need to encode (full_text mode or missing embedding)
                jobs_needing_encoding.append(job)

        load_time = time.time() - load_start

        # Encode jobs that don't have pre-computed embeddings (fallback)
        encode_start = time.time()
        for job in jobs_needing_encoding:
            # Build job text based on mode
            if match_mode == 'title_only':
                job_text = job.get('title', '')
            else:  # full_text
                parts = []
                if job.get('title'):
                    parts.append(job['title'])
                    parts.append(job['title'])  # Add title twice for emphasis
                if job.get('company'):
                    parts.append(f"Company: {job['company']}")
                if job.get('location'):
                    parts.append(f"Location: {job['location']}")
                if job.get('description'):
                    desc = job['description'][:3000]
                    parts.append(desc)
                job_text = " ".join(parts)

            # Encode job on-the-fly
            job_embedding = model.encode(job_text, show_progress_bar=False)
            job_embeddings[job['id']] = job_embedding

        encode_time = time.time() - encode_start

        # Calculate similarity for all jobs
        results = []
        for job in jobs:
            job_embedding = job_embeddings.get(job['id'])
            if job_embedding is None:
                continue

            # Calculate cosine similarity
            similarity = float(np.dot(query_embedding, job_embedding) /
                             (np.linalg.norm(query_embedding) * np.linalg.norm(job_embedding)))

            if similarity >= threshold:
                results.append({
                    'job_id': job['id'],
                    'title': job['title'],
                    'company': job['company'],
                    'location': job['location'],
                    'url': job['url'],
                    'discovered_date': job['discovered_date'].isoformat() if hasattr(job['discovered_date'], 'isoformat') else str(job['discovered_date']),
                    'similarity': round(similarity, 4),
                    'match_score': int(similarity * 100)
                })

        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)

        # Limit results
        results = results[:limit]

        total_time = time.time() - start_time

        # Calculate speedup stats
        precomputed_count = len(job_embeddings) - len(jobs_needing_encoding)
        onthefly_count = len(jobs_needing_encoding)

        return jsonify({
            'results': results,
            'stats': {
                'total_jobs': len(jobs),
                'matches_found': len(results),
                'threshold': threshold,
                'match_mode': match_mode,
                'model': model_name,
                'query': query,
                'locations': locations,
                'include_remote': include_remote,
                'embeddings': {
                    'precomputed': precomputed_count,
                    'encoded_onthefly': onthefly_count,
                    'coverage': round(precomputed_count / len(jobs) * 100, 1) if len(jobs) > 0 else 0
                },
                'timings': {
                    'fetch_jobs': round(fetch_time, 3),
                    'encode_query': round(query_encode_time, 3),
                    'load_embeddings': round(load_time, 3),
                    'encode_jobs': round(encode_time, 3),
                    'total': round(total_time, 3)
                }
            }
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/suggest-search')
@login_required
def suggest_search():
    """Show search suggestion interface"""
    user, stats = get_user_context()
    
    # Check if user has a CV profile
    cv_profile = cv_manager.get_profile_by_user(user['id'])
    
    if not cv_profile:
        flash('Please upload your CV first to get personalized search suggestions', 'warning')
        return redirect(url_for('upload_cv'))
    
    return render_template('suggest_search.html', user=user, stats=stats)


@app.route('/get-suggestions', methods=['POST'])
@login_required
def get_suggestions():
    """Get AI-powered search suggestions based on CV"""
    user, stats = get_user_context()
    
    # Get CV profile
    cv_profile = cv_manager.get_profile_by_user(user['id'])
    
    if not cv_profile:
        return {'error': 'No CV profile found'}, 400
    
    try:
        # Initialize suggester
        api_key = os.getenv('ANTHROPIC_API_KEY')
        suggester = SearchSuggester(api_key)
        
        # Get suggestions
        suggestions = suggester.suggest_search_parameters(cv_profile)
        
        return {'suggestions': suggestions}, 200
        
    except Exception as e:
        return {'error': str(e)}, 500


@app.route('/run-custom-search', methods=['POST'])
@login_required
def run_custom_search():
    """Run job search with selected parameters"""
    from collectors.jsearch import JSearchCollector
    from analysis.claude_analyzer import ClaudeJobAnalyzer
    import time
    
    user, stats = get_user_context()
    
    # Get selected parameters from form
    selected_titles = request.form.getlist('job_titles[]')
    selected_locations = request.form.getlist('locations[]')
    
    if not selected_titles or not selected_locations:
        flash('Please select at least one job title and location', 'error')
        return redirect(url_for('suggest_search'))
    
    try:
        # Initialize collectors
        jsearch_api_key = os.getenv('JSEARCH_API_KEY')
        
        if not jsearch_api_key:
            flash('JSearch API not configured', 'error')
            return redirect(url_for('jobs'))
        
        # Load config for filtering settings
        config = load_config('config.yaml')
        source_config = config.get('preferences', {}).get('source_filtering', {})
        enable_filtering = source_config.get('enabled', True)
        min_quality = source_config.get('min_quality', 2)
        
        jsearch = JSearchCollector(
            jsearch_api_key,
            enable_filtering=enable_filtering,
            min_quality=min_quality
        )
        
        # Collect jobs
        all_jobs = []
        
        flash(f'Searching for {len(selected_titles)} job titles in {len(selected_locations)} locations...', 'info')
        
        # Limit to avoid rate limits (max 15 searches)
        max_searches = 15
        search_count = 0
        
        for title in selected_titles:
            if search_count >= max_searches:
                break
            for location in selected_locations:
                if search_count >= max_searches:
                    break
                    
                # Map country codes
                country = 'de' if 'Germany' in location or 'Deutschland' in location else None
                
                jobs = jsearch.search_jobs(
                    query=title,
                    location=location,
                    num_pages=1,
                    date_posted="week",
                    country=country
                )
                all_jobs.extend(jobs)
                search_count += 1
                time.sleep(0.5)  # Rate limit
        
        # Deduplicate
        from utils.helpers import deduplicate_jobs
        all_jobs = deduplicate_jobs(all_jobs)
        
        # Filter new jobs
        from utils.helpers import filter_new_jobs
        new_jobs = filter_new_jobs(all_jobs, job_db)
        
        if not new_jobs:
            flash(f'Found {len(all_jobs)} jobs, but all were already in database', 'info')
            return redirect(url_for('jobs'))
        
        # Analyze with Claude
        api_key = os.getenv('ANTHROPIC_API_KEY')
        analyzer = ClaudeJobAnalyzer(api_key, model="claude-3-haiku-20240307")
        
        # Use CV profile
        cv_profile = cv_manager.get_profile_by_user(user['id'])
        if cv_profile:
            analyzer.set_profile_from_cv(cv_profile)
        
        analyzed_jobs = analyzer.analyze_batch(new_jobs)
        
        # Store in database
        stored_count = 0
        for job in analyzed_jobs:
            job['user_id'] = user['id']
            if cv_profile:
                job['cv_profile_id'] = cv_profile.get('id')
            
            job_id = job_db.add_job(job)
            if job_id:
                stored_count += 1
        
        flash(f'✓ Found and analyzed {stored_count} new jobs!', 'success')
        return redirect(url_for('jobs'))
        
    except Exception as e:
        flash(f'Error running search: {str(e)}', 'error')
        return redirect(url_for('suggest_search'))


@app.route('/jobs/<int:job_id>')
@login_required
def job_detail(job_id):
    """Job detail page with user-specific match data"""
    # Get current user
    user, stats = get_user_context()
    user_id = user['id']

    # Get job with user-specific data merged (priority, match_reasoning, etc.)
    job = job_db.get_job_with_user_data(job_id, user_id)

    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('jobs'))

    # Note: match_score, priority, match_reasoning, key_alignments, and potential_gaps
    # are already set and parsed by get_job_with_user_data()

    # Fetch User Profile for accurate matching
    user_cv_profile = cv_manager.get_primary_profile(user_id)
    
    user_skills = set()
    user_competencies = set()
    
    if user_cv_profile:
        # Normalize for matching
        raw_skills = user_cv_profile.get('technical_skills', []) or []
        user_skills = set(str(s).lower().strip() for s in raw_skills)
        
        raw_comps = user_cv_profile.get('competencies', []) or []
        user_competencies = set(str(c).lower().strip() for c in raw_comps)

    # Calculate match status for UI visualization
    if job:
        # Debug: Check what we got from database
        print(f"DEBUG job_detail: competency_mappings type={type(job.get('competency_mappings'))}, value={job.get('competency_mappings')}")
        print(f"DEBUG job_detail: skill_mappings type={type(job.get('skill_mappings'))}, value={job.get('skill_mappings')}")
        print(f"DEBUG job_detail: ai_competencies exists? {job.get('ai_competencies') is not None}, count={len(job.get('ai_competencies') or [])}")
        print(f"DEBUG job_detail: ai_key_skills exists? {job.get('ai_key_skills') is not None}, count={len(job.get('ai_key_skills') or [])}")

        # 1. Competencies Matching (HYBRID: Claude → Keyword → Semantic)
        if job.get('ai_competencies'):
            matches = {}

            # Option 1: Try using Claude's structured mappings first (NEW JOBS)
            claude_comp_mappings = job.get('competency_mappings')
            if claude_comp_mappings and isinstance(claude_comp_mappings, list):
                # Use Claude's expert mappings
                print(f"✨ Using Claude competency mappings ({len(claude_comp_mappings)} mappings)")
                mapped_comps = set()
                for mapping in claude_comp_mappings:
                    if isinstance(mapping, dict):
                        job_req = mapping.get('job_requirement', '')
                        if job_req:
                            matches[job_req] = True
                            mapped_comps.add(job_req.lower())
                
                # Mark unmapped competencies as unmatched
                for comp in job['ai_competencies']:
                    if comp.lower() not in mapped_comps:
                        matches[comp] = False
            else:
                # Option 2: Fallback to keyword/semantic matching (EXISTING JOBS)
                print(f"🔄 Using fallback matching for competencies")
                
                # Prepare alignment texts (from Claude's reasoning)
                align_texts = []
                if job.get('key_alignments'):
                    for a in job['key_alignments']:
                        if isinstance(a, str):
                            align_texts.append(a.lower())
                        elif isinstance(a, dict):
                            align_texts.append(str(a.get('text', '')).lower())
                
                for comp in job['ai_competencies']:
                    is_matched = False
                    comp_lower = comp.lower().strip()
                    
                    # A. Check User Profile directly (Strongest evidence)
                    if comp_lower in user_competencies or comp_lower in user_skills:
                        is_matched = True
                    
                    # Fuzzy profile match
                    if not is_matched and (user_competencies or user_skills):
                         all_user_terms = user_competencies.union(user_skills)
                         for term in all_user_terms:
                             if term and (comp_lower in term or term in comp_lower):
                                 if len(term) > 3 and len(comp_lower) > 3:
                                     is_matched = True
                                     break

                    # B. Check against Key Alignments
                    if not is_matched and align_texts:
                        for align in align_texts:
                            if comp_lower in align:
                                is_matched = True
                                break
                        
                        if not is_matched:
                            comp_words = set(w for w in comp_lower.split() if len(w) > 3)
                            if comp_words:
                                for align in align_texts:
                                    align_words = set(w for w in align.split() if len(w) > 3)
                                    overlap = comp_words.intersection(align_words)
                                    if len(overlap) / len(comp_words) >= 0.5:
                                        is_matched = True
                                        break
                                
                    matches[comp] = is_matched
                
                # C. Semantic matching fallback for unmatched competencies
                unmatched_comps = [comp for comp, matched in matches.items() if not matched]
                if unmatched_comps and user_cv_profile:
                    try:
                        from src.analysis.semantic_matcher import get_semantic_matcher
                        semantic_matcher = get_semantic_matcher()
                        
                        user_comp_list = user_cv_profile.get('competencies', []) or []
                        user_skill_list = user_cv_profile.get('technical_skills', []) or []
                        
                        # Parse JSON if needed
                        import json
                        if isinstance(user_comp_list, str):
                            try:
                                user_comp_list = json.loads(user_comp_list)
                            except:
                                user_comp_list = []
                        if isinstance(user_skill_list, str):
                            try:
                                user_skill_list = json.loads(user_skill_list)
                            except:
                                user_skill_list = []
                        
                        # Extract 'name' from competency dicts
                        comp_names = []
                        for comp in user_comp_list:
                            if isinstance(comp, dict):
                                comp_names.append(comp.get('name', str(comp)))
                            else:
                                comp_names.append(str(comp))
                        
                        skill_names = [str(s) for s in user_skill_list]
                        
                        semantic_matches = semantic_matcher.match_competencies(
                            unmatched_comps,
                            comp_names,
                            skill_names,
                            threshold=0.45
                        )
                        
                        # Update matches with semantic results
                        for comp, sem_matched in semantic_matches.items():
                            if sem_matched:
                                matches[comp] = True
                                print(f"✓ Semantic match: {comp}")
                                
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Semantic matching failed: {e}")
            
            job['competency_match_map'] = matches

        # 2. Skills Matching (HYBRID: Claude → Keyword → Semantic)
        if job.get('ai_key_skills'):
            skill_matches = {}
            
            # Option 1: Try using Claude's structured skill mappings first (NEW JOBS)
            claude_skill_mappings = job.get('skill_mappings')
            if claude_skill_mappings and isinstance(claude_skill_mappings, list):
                # Use Claude's expert mappings
                print(f"✨ Using Claude skill mappings ({len(claude_skill_mappings)} mappings)")
                mapped_skills = set()
                for mapping in claude_skill_mappings:
                    if isinstance(mapping, dict):
                        job_skill = mapping.get('job_skill', '')
                        if job_skill:
                            skill_matches[job_skill] = True
                            mapped_skills.add(job_skill.lower())
                
                # Mark unmapped skills as unmatched
                for skill in job['ai_key_skills']:
                    if skill.lower() not in mapped_skills:
                        skill_matches[skill] = False
            else:
                # Option 2: Fallback to keyword/semantic matching (EXISTING JOBS)
                print(f"🔄 Using fallback matching for skills")
                
                for skill in job['ai_key_skills']:
                    s_lower = str(skill).lower().strip()
                    is_matched = False
                    
                    # Check direct match
                    if s_lower in user_skills:
                        is_matched = True
                    
                    # Check fuzzy match
                    if not is_matched:
                         for us in user_skills:
                             if len(us) > 2 and len(s_lower) > 2:
                                 if s_lower in us or us in s_lower:
                                     is_matched = True
                                     break
                    
                    skill_matches[skill] = is_matched
                
                # C. Semantic matching fallback for unmatched skills
                unmatched_skills = [skill for skill, matched in skill_matches.items() if not matched]
                if unmatched_skills and user_cv_profile:
                    try:
                        from src.analysis.semantic_matcher import get_semantic_matcher
                        semantic_matcher = get_semantic_matcher()
                        
                        user_skill_list = user_cv_profile.get('technical_skills', []) or []
                        
                        # Parse JSON if needed
                        import json
                        if isinstance(user_skill_list, str):
                            try:
                                user_skill_list = json.loads(user_skill_list)
                            except:
                                user_skill_list = []
                        
                        # Extract names if dict format
                        skill_names = []
                        for s in user_skill_list:
                            if isinstance(s, dict):
                                skill_names.append(s.get('name', str(s)))
                            else:
                                skill_names.append(str(s))
                        
                        semantic_matches = semantic_matcher.match_skills(
                            unmatched_skills,
                            skill_names,
                            threshold=0.45
                        )
                        
                        # Update matches with semantic results
                        for skill, sem_matched in semantic_matches.items():
                            if sem_matched:
                                skill_matches[skill] = True
                                print(f"✓ Semantic skill match: {skill}")
                                
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Semantic skill matching failed: {e}")
            
            job['skill_match_map'] = skill_matches

    # Normalize work_history to work_experience for frontend compatibility
    if user_cv_profile and 'work_history' in user_cv_profile:
        work_experiences = []
        for wh in user_cv_profile.get('work_history', []):
            # Parse duration string (e.g., "Jul 2021 - Present")
            duration = wh.get('duration', '')
            parts = duration.split(' - ')
            start_date = parts[0] if parts else ''
            end_date = parts[1] if len(parts) > 1 else 'Present'

            work_experiences.append({
                'title': wh.get('title', ''),
                'company': wh.get('company', ''),
                'start_date': start_date,
                'end_date': end_date,
                'description': wh.get('description', ''),
                'key_achievements': wh.get('key_achievements', [])
            })
        user_cv_profile['work_experience'] = work_experiences

    return render_template('job_detail.html', job=job, user_profile=user_cv_profile)


@app.route('/jobs/<int:job_id>/generate-cover-letter')
def generate_cover_letter_page(job_id):
    """Cover letter generation page"""
    user, stats = get_user_context()
    
    # Get job
    job = job_db.get_job(job_id)

    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('jobs'))
    
    # Check if user has CV profile
    cv_profile = cv_manager.get_profile_by_user(user['id'])
    
    if not cv_profile:
        flash('Please upload your CV first to generate cover letters', 'warning')
        return redirect(url_for('upload_cv'))
    
    # Get available styles
    api_key = os.getenv('ANTHROPIC_API_KEY')
    generator = CoverLetterGenerator(api_key)
    styles = generator.STYLES
    
    return render_template('generate_cover_letter.html', 
                         job=job, 
                         styles=styles,
                         user=user,
                         stats=stats)


@app.route('/jobs/<int:job_id>/create-cover-letter', methods=['POST'])
@login_required
def create_cover_letter(job_id):
    """Generate cover letter"""
    user, stats = get_user_context()
    
    # Get parameters
    style = request.form.get('style', 'professional')
    language = request.form.get('language', 'english')
    
    # Get job
    job = job_db.get_job(job_id)

    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('jobs'))
    
    # Get CV profile
    cv_profile = cv_manager.get_profile_by_user(user['id'])
    
    if not cv_profile:
        flash('Please upload your CV first', 'warning')
        return redirect(url_for('upload_cv'))
    
    try:
        # Generate cover letter
        api_key = os.getenv('ANTHROPIC_API_KEY')
        generator = CoverLetterGenerator(api_key)
        
        result = generator.generate_cover_letter(
            cv_profile=cv_profile,
            job=job,
            style=style,
            language=language
        )
        
        if 'error' in result:
            flash(f"Error: {result['error']}", 'error')
            return redirect(url_for('generate_cover_letter_page', job_id=job_id))
        
        return render_template('cover_letter_result.html',
                             result=result,
                             job=job,
                             user=user,
                             stats=stats)
        
    except Exception as e:
        flash(f'Error generating cover letter: {str(e)}', 'error')
        return redirect(url_for('generate_cover_letter_page', job_id=job_id))


@app.route('/jobs/<int:job_id>/status/<status>', methods=['GET', 'POST'])
def update_job_status(job_id, status):
    """Update job status"""
    try:
        # Get job to verify it exists
        job = job_db.get_job(job_id)

        if job:
            job_db.update_job_status(job['id'], status)
            flash(f'Job marked as {status}', 'success')
        else:
            flash('Job not found', 'error')
    except Exception as e:
        flash(f'Error updating job: {str(e)}', 'error')

    return redirect(url_for('jobs'))



# Deprecated: run_search_background removed - use run_job_matching instead
    """Run job search in background with progress updates"""
    
    def send_progress(percent, message, msg_type='info'):
        """Send progress update"""
        if search_id in search_progress:
            search_progress[search_id].put({
                'type': 'progress',
                'percent': percent,
                'message': message,
                'msg_type': msg_type
            })
    
    def send_complete(message):
        """Send completion message"""
        if search_id in search_progress:
            search_progress[search_id].put({
                'type': 'complete',
                'message': message
            })
    
    def send_error(message):
        """Send error message"""
        if search_id in search_progress:
            search_progress[search_id].put({
                'type': 'error',
                'message': message
            })
    
    try:
        send_progress(5, "Loading configuration...")
        
        # Import required modules
        from collectors.indeed import IndeedCollector
        from collectors.jsearch import JSearchCollector
        from utils.helpers import deduplicate_jobs, filter_new_jobs, categorize_jobs
        import yaml
        
        # Load config
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        send_progress(10, "Getting your CV profile...")
        
        # Get user's CV profile
        cv_profile = cv_manager.get_profile_by_user(user['id'])
        if not cv_profile:
            send_error('Please upload your CV first before running a search')
            return
        
        send_progress(15, "Loading search preferences...")
        
        # Get user's search preferences
        user_prefs = cv_manager.get_user_search_preferences(user['id'])
        keywords = user_prefs['keywords'] if user_prefs['keywords'] else config['search_config']['keywords']
        locations = user_prefs['locations'] if user_prefs['locations'] else config['search_config']['locations']
        
        if not keywords or not locations:
            send_error('Please configure your search preferences first')
            return
        
        prefs_source = "custom preferences" if user_prefs['keywords'] else "default configuration"
        send_progress(20, f"Using {prefs_source}: {len(keywords)} keywords, {len(locations)} locations")
        
        # Initialize collectors
        collectors = []
        source_config = config.get('preferences', {}).get('source_filtering', {})
        
        # Active Jobs DB API (Re-enabled - hourly rate limit should be reset)
        activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')
        
        if activejobs_key:
            collectors.append(('ActiveJobs', ActiveJobsCollector(
                activejobs_key,
                enable_filtering=source_config.get('enabled', True),
                min_quality=source_config.get('min_quality', 2)
            )))
            send_progress(18, "Initialized Active Jobs DB (5000 jobs/month, 40k-50k Germany jobs)")
        
        # Adzuna API (Disabled - poor Germany coverage)
        # adzuna_id = os.getenv('ADZUNA_APP_ID')
        # adzuna_key = os.getenv('ADZUNA_APP_KEY')
        # 
        # if adzuna_id and adzuna_key:
        #     collectors.append(('Adzuna', AdzunaCollector(
        #         adzuna_id,
        #         adzuna_key,
        #         enable_filtering=source_config.get('enabled', True),
        #         min_quality=source_config.get('min_quality', 2)
        #     )))
        #     send_progress(20, "Initialized Adzuna collector (250 requests/month)")
        
        # JSearch API (Re-enable to test if quota reset)
        jsearch_key = os.getenv('JSEARCH_API_KEY')
        
        if jsearch_key and jsearch_key != 'your_rapidapi_key_for_jsearch':
            collectors.append(('JSearch', JSearchCollector(
                jsearch_key,
                enable_filtering=source_config.get('enabled', True),
                min_quality=source_config.get('min_quality', 2)
            )))
            send_progress(25, "Initialized JSearch collector (LinkedIn, Google Jobs, Indeed)")
        
        if not collectors:
            send_error('No job collectors configured. All API quotas exhausted. Please upgrade your plan or wait for monthly reset.')
            return
        
        # Collect jobs
        send_progress(30, f"Starting job collection: {len(keywords) * len(locations)} searches...")
        all_jobs = []
        total_searches = len(keywords) * len(locations)
        search_count = 0
        
        for name, collector in collectors:
            for keyword in keywords:
                for location in locations:
                    search_count += 1
                    progress_percent = 30 + int((search_count / total_searches) * 40)
                    send_progress(progress_percent, f"[{search_count}/{total_searches}] {name}: '{keyword}' in '{location}'")
                    
                    try:
                        # Determine country code
                        country = 'de'  # Default to Germany
                        if 'germany' in location.lower() or 'deutschland' in location.lower():
                            country = 'de'
                        elif 'remote' in location.lower():
                            country = 'de'  # Assume remote in Germany
                        
                        if name == 'ActiveJobs':
                            results = collector.search_jobs(
                                query=keyword,
                                location=location,
                                num_pages=1,
                                results_per_page=5,  # Reduced from 10 to 5 to speed up searches
                                date_posted="week",
                                description_type="text"
                            )
                        elif name == 'Adzuna':
                            results = collector.search_jobs(
                                query=keyword,
                                location=location,
                                num_pages=1,
                                results_per_page=5,  # Reduced from 10 to 5
                                country=country,
                                max_days_old=7
                            )
                        elif name == 'JSearch':
                            results = collector.search_jobs(
                                query=keyword,
                                location=location,
                                num_pages=1,
                                date_posted="week",
                                country=country
                            )
                        else:
                            results = []
                        
                        all_jobs.extend(results)
                        if results:
                            send_progress(progress_percent, f"  → Found {len(results)} jobs", 'success')
                        
                        # Reduced delay to prevent Railway timeout (was 3s, now 0.5s)
                        # Railway has ~300s timeout, with 90 searches: 0.5s delay = 45s of waiting vs 270s
                        if search_count < total_searches:
                            time.sleep(0.5)
                            
                    except Exception as e:
                        send_progress(progress_percent, f"  → Error: {str(e)}", 'warning')
        
        send_progress(70, f"Collection complete! Found {len(all_jobs)} total jobs", 'success')
        
        # Process jobs
        send_progress(72, "Removing duplicates...")
        unique_jobs = deduplicate_jobs(all_jobs)
        send_progress(74, f"Filtered to {len(unique_jobs)} unique jobs")
        
        send_progress(76, "Checking against database...")
        new_jobs = filter_new_jobs(unique_jobs, job_db)
        send_progress(78, f"Found {len(new_jobs)} new jobs to analyze")
        
        if not new_jobs:
            send_complete(f'No new jobs found. Checked {len(all_jobs)} listings, all were duplicates or previously seen.')
            return
        
        # Analyze jobs
        send_progress(80, f"Analyzing {len(new_jobs)} jobs with Claude AI...")
        from analysis.claude_analyzer import ClaudeJobAnalyzer
        
        # Initialize analyzer
        api_key = os.getenv('ANTHROPIC_API_KEY')
        analyzer = ClaudeJobAnalyzer(
            api_key=api_key,
            model=config.get('analysis', {}).get('model', 'claude-3-5-haiku-20241022'),
            db=job_db,
            user_email=user['email']
        )
        
        # Set CV profile for analysis
        analyzer.set_profile_from_cv(cv_profile.get('parsed_cv', {}))
        
        analyzed_jobs = []
        for idx, job in enumerate(new_jobs, 1):
            progress_percent = 80 + int((idx / len(new_jobs)) * 15)
            send_progress(progress_percent, f"Analyzing job {idx}/{len(new_jobs)}: {job.get('title', 'Unknown')}")
            
            analyzed = analyzer.analyze_job(job)
            if analyzed:
                analyzed_jobs.append(analyzed)
        
        send_progress(95, f"Analysis complete! {len(analyzed_jobs)} jobs scored", 'success')
        
        # Store jobs and create user matches
        send_progress(96, "Saving jobs to database...")
        stored_count = 0
        matched_count = 0
        for job in analyzed_jobs:
            job['user_id'] = user['id']
            job['cv_profile_id'] = cv_profile.get('id')
            job_id = job_db.add_job(job)
            if job_id:
                stored_count += 1
                # Create user_job_match entry
                match_success = job_db.add_user_job_match(
                    user_id=user['id'],
                    job_id=job_id,
                    claude_score=job.get('match_score'),
                    priority=job.get('priority', 'medium'),
                    match_reasoning=job.get('match_reasoning'),
                    key_alignments=job.get('key_alignments', []),
                    potential_gaps=job.get('potential_gaps', [])
                )
                if match_success:
                    matched_count += 1
        
        categorized = categorize_jobs(analyzed_jobs)
        
        send_progress(98, f"Stored {stored_count} jobs, created {matched_count} matches", 'success')
        send_progress(100, f"Complete!", 'success')
        
        summary = f"Found {stored_count} new jobs: {len(categorized['high'])} high priority, {len(categorized['medium'])} medium, {len(categorized['low'])} low priority"
        send_complete(summary)
        
    except Exception as e:
        send_error(f'Search error: {str(e)}')
        print(f"Search error: {e}")
        import traceback
        traceback.print_exc()


# Deprecated: search_stream removed - use matching-status instead

@app.errorhandler(404)
def not_found(e):
    """Stream search progress via Server-Sent Events"""
    search_id = session.get('current_search_id')
    
    if not search_id or search_id not in search_progress:
        def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No active search found'})}\n\n"
        return Response(error_stream(), mimetype='text/event-stream')
    
    def generate():
        q = search_progress[search_id]
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    
                    if msg['type'] == 'progress':
                        yield f"event: progress\ndata: {json.dumps({'percent': msg['percent'], 'message': msg['message'], 'type': msg.get('msg_type', 'info')})}\n\n"
                    elif msg['type'] == 'complete':
                        yield f"event: complete\ndata: {json.dumps({'message': msg['message']})}\n\n"
                        break
                    elif msg['type'] == 'error':
                        yield f"event: error\ndata: {json.dumps({'message': msg['message']})}\n\n"
                        break
                        
                except queue.Empty:
                    # Keepalive ping
                    yield f": keepalive\n\n"
                    
        finally:
            # Cleanup
            if search_id in search_progress:
                del search_progress[search_id]
    
    return Response(generate(), mimetype='text/event-stream')


@app.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return render_template('base.html'), 404


@app.route('/dashboard')
def dashboard():
    """Application dashboard - shows jobs user wants to apply to"""
    user, stats = get_user_context()
    
    # Get shortlisted jobs
    shortlisted_jobs = job_db.get_shortlisted_jobs(user['email'])
    
    # Parse JSON fields
    for job in shortlisted_jobs:
        if job.get('key_alignments') and isinstance(job['key_alignments'], str):
            try:
                job['key_alignments'] = json.loads(job['key_alignments'])
            except:
                job['key_alignments'] = []
        
        if job.get('potential_gaps') and isinstance(job['potential_gaps'], str):
            try:
                job['potential_gaps'] = json.loads(job['potential_gaps'])
            except:
                job['potential_gaps'] = []
    
    # Get feedback learning summary
    from analysis.feedback_learner import FeedbackLearner
    learner = FeedbackLearner(job_db)
    learning_summary = learner.get_preference_summary(user['email'])
    
    return render_template('dashboard.html', 
                         user=user, 
                         stats=stats, 
                         jobs=shortlisted_jobs,
                         learning_summary=learning_summary)


@app.route('/cost-dashboard')
@login_required
def cost_dashboard():
    """Cost tracking dashboard - shows usage and billing information"""
    user, stats = get_user_context()
    
    # TODO: Once cost_sessions table is created, fetch real data
    # For now, show placeholder data
    
    return render_template('cost_dashboard.html',
                         user=user,
                         stats=stats,
                         total_month=0.00,
                         total_30days=0.00,
                         session_count=0,
                         avg_session=0.00,
                         sessions=[])


@app.route('/learning-insights')
def learning_insights():
    """Show what the AI has learned from user feedback"""
    user, stats = get_user_context()
    
    from analysis.feedback_learner import FeedbackLearner
    learner = FeedbackLearner(job_db)
    
    # Get detailed preferences analysis
    preferences = learner.analyze_user_preferences(user['email'])
    
    # Get the actual learning context that Claude sees
    learning_context = learner.generate_learning_context(user['email'])
    
    # Get recent feedback history
    feedback_history = job_db.get_user_feedback(user['email'], limit=20)
    
    return render_template('learning_insights.html',
                         user=user,
                         stats=stats,
                         preferences=preferences,
                         learning_context=learning_context,
                         feedback_history=feedback_history)


@app.route('/my-resumes')
@login_required
def my_resumes():
    """View all generated resumes for current user"""
    user, stats = get_user_context()
    user_id = get_user_id()

    if not resume_ops:
        flash('Resume feature not available', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Get all resumes for this user
        resumes = resume_ops.get_user_resumes(user_id)

        # Enrich with job details
        for resume in resumes:
            job = job_db.get_job_by_id(resume['job_id'])
            if job:
                resume['job_title'] = job.get('title', 'Unknown Job')
                resume['job_company'] = job.get('company', 'Unknown Company')
            else:
                resume['job_title'] = 'Job Not Found'
                resume['job_company'] = ''

            # Check if PDF exists
            pdf_path = resume.get('resume_pdf_path')
            resume['pdf_exists'] = pdf_path and os.path.exists(pdf_path)

        return render_template('my_resumes.html',
                             user=user,
                             stats=stats,
                             resumes=resumes)

    except Exception as e:
        print(f"Error loading resumes: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading resumes: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/my-resumes/<int:resume_id>/delete', methods=['POST'])
@login_required
def delete_resume_route(resume_id):
    """Delete a generated resume"""
    user_id = get_user_id()

    if not resume_ops:
        flash('Resume feature not available', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Delete from database (with user verification)
        deleted = resume_ops.delete_resume(resume_id, user_id)

        if deleted:
            flash('Resume deleted successfully', 'success')
        else:
            flash('Resume not found or access denied', 'error')

    except Exception as e:
        print(f"Error deleting resume: {e}")
        flash(f'Error deleting resume: {str(e)}', 'error')

    return redirect(url_for('my_resumes'))


@app.route('/jobs/<int:job_id>/shortlist', methods=['POST'])
@login_required
def shortlist_job(job_id):
    """Add job to shortlist (user-specific)"""
    try:
        user_id = get_user_id()
        job_db.update_user_job_status(user_id, job_id, 'shortlisted')
        flash('Job added to your dashboard!', 'success')
    except Exception as e:
        flash(f'Error adding job to shortlist: {str(e)}', 'error')

    return redirect(request.referrer or url_for('jobs'))


@app.route('/jobs/<int:job_id>/remove-shortlist', methods=['POST'])
@login_required
def remove_shortlist(job_id):
    """Remove job from shortlist (user-specific)"""
    try:
        user_id = get_user_id()
        job_db.update_user_job_status(user_id, job_id, 'viewed')
        flash('Job removed from dashboard', 'info')
    except Exception as e:
        flash(f'Error removing job: {str(e)}', 'error')

    return redirect(request.referrer or url_for('dashboard'))


@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    """
    Hide job permanently for this user - it won't appear in future searches
    Job is marked as 'deleted' in user_job_matches (user-specific)
    """
    try:
        user_id = get_user_id()
        job_db.update_user_job_status(user_id, job_id, 'deleted')
        flash('Job hidden permanently. It will not appear in future searches.', 'success')
    except Exception as e:
        flash(f'Error hiding job: {str(e)}', 'error')

    return redirect(url_for('jobs'))


@app.route('/deleted-jobs')
@login_required
def deleted_jobs():
    """View all deleted/hidden jobs"""
    user, stats = get_user_context()
    user_id = get_user_id()

    deleted_jobs_list = job_db.get_deleted_jobs(user_id=user_id, limit=100)
    
    # Parse JSON fields
    for job in deleted_jobs_list:
        if job.get('key_alignments') and isinstance(job['key_alignments'], str):
            try:
                job['key_alignments'] = json.loads(job['key_alignments'])
            except:
                job['key_alignments'] = []
        
        if job.get('potential_gaps') and isinstance(job['potential_gaps'], str):
            try:
                job['potential_gaps'] = json.loads(job['potential_gaps'])
            except:
                job['potential_gaps'] = []
    
    return render_template('deleted_jobs.html',
                         user=user,
                         stats=stats,
                         jobs=deleted_jobs_list)


@app.route('/jobs/<int:job_id>/restore', methods=['POST'])
def restore_job(job_id):
    """Restore a deleted job back to 'new' status"""
    try:
        job_db.update_job_status(job_id, 'new')
        flash('Job restored successfully', 'success')
    except Exception as e:
        flash(f'Error restoring job: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('deleted_jobs'))


@app.route('/jobs/<int:job_id>/permanent-delete', methods=['POST'])
def permanent_delete(job_id):
    """Permanently remove job from database (cannot be undone)"""
    try:
        if job_db.permanently_delete_job(job_id):
            flash('Job permanently deleted from database', 'success')
        else:
            flash('Error deleting job', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('deleted_jobs'))


@app.route('/jobs/<int:job_id>/feedback', methods=['POST'])
def job_feedback(job_id):
    """Submit feedback on job match score"""
    user, _ = get_user_context()
    
    feedback_type = request.form.get('feedback_type')  # agree, disagree, too_high, too_low
    user_score = request.form.get('user_score', type=int)
    feedback_reason = request.form.get('feedback_reason', '')
    
    # Get original job score
    # Get original job score for this user
    conn = job_db._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT claude_score FROM user_job_matches WHERE job_id = %s AND user_id = %s', (job_id, user['id']))
        row = cursor.fetchone()
    finally:
        # Proper pool management
        cursor.close()
        job_db._return_connection(conn)
    
    # If no match record found, default to 0
    original_score = row[0] if row else 0
    
    # Save feedback
    success = job_db.add_feedback(
        job_id=job_id,
        user_email=user['email'],
        feedback_type=feedback_type,
        match_score_original=original_score,
        match_score_user=user_score,
        feedback_reason=feedback_reason
    )
    
    if success:
        flash('Thank you for your feedback! The system will learn from this.', 'success')
    else:
        flash('Error saving feedback', 'error')
    
    return redirect(request.referrer or url_for('jobs'))


@app.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return render_template('base.html'), 404


@app.route('/search-preferences')
def search_preferences():
    """Show search preferences configuration page"""
    user, stats = get_user_context()
    
    # Get user's current preferences
    user_prefs = cv_manager.get_user_search_preferences(user['id'])
    
    # Convert lists to newline-separated strings for textarea
    keywords_text = '\n'.join(user_prefs['keywords']) if user_prefs['keywords'] else ''
    locations_text = '\n'.join(user_prefs['locations']) if user_prefs['locations'] else ''
    
    # Load default config for comparison
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    has_preferences = bool(user_prefs['keywords'] or user_prefs['locations'])
    
    return render_template('search_preferences.html',
                         user=user,
                         stats=stats,
                         keywords=keywords_text,
                         locations=locations_text,
                         has_preferences=has_preferences,
                         default_config=config.get('search_config', {}))


@app.route('/update-search-preferences', methods=['POST'])
@login_required
def update_search_preferences():
    """Update user's search preferences and trigger backfill"""
    user, stats = get_user_context()

    try:
        # Get form data
        keywords_text = request.form.get('keywords', '').strip()
        locations_text = request.form.get('locations', '').strip()

        # Convert newline-separated text to lists
        keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        locations = [l.strip() for l in locations_text.split('\n') if l.strip()]

        # Validate
        if not keywords:
            flash('Please enter at least one job keyword', 'error')
            return redirect(url_for('search_preferences'))

        if not locations:
            flash('Please enter at least one location', 'error')
            return redirect(url_for('search_preferences'))

        # Update user's preference JSON (for backward compatibility)
        cv_manager.update_user_search_preferences(
            user['id'],
            keywords=keywords,
            locations=locations
        )

        # Deactivate old queries in user_search_queries table
        cv_manager.deactivate_user_search_queries(user['id'])

        # Add new normalized queries to user_search_queries table
        row_count = cv_manager.add_user_search_queries(
            user_id=user['id'],
            query_name='Updated Search Preferences',
            title_keywords=keywords,
            locations=locations,
            ai_work_arrangement=None,  # TODO: Add to preferences form
            ai_seniority=None,  # TODO: Add to preferences form
            ai_employment_type=None,
            ai_industry=None,
            priority=10
        )

        print(f"✓ Updated search preferences: {len(keywords)} keywords × {len(locations)} locations = {row_count} queries", flush=True)

        # Trigger NEW backfill system (with deduplication)
        try:
            from src.jobs.user_backfill import backfill_user_on_signup
            print(f"🔄 Triggering backfill for updated preferences...", flush=True)

            backfill_stats = backfill_user_on_signup(
                user_id=user['id'],
                user_email=user['email'],
                db=cv_manager
            )

            if backfill_stats.get('already_backfilled'):
                flash(f'Search preferences updated! ({row_count} combinations, already backfilled by other users)', 'success')
            elif backfill_stats.get('error'):
                flash(f'Search preferences updated! {backfill_stats.get("error")}', 'warning')
            else:
                new_jobs = backfill_stats.get('new_jobs_added', 0)
                flash(f'Search preferences updated! Loaded {new_jobs} new jobs from {row_count} combinations.', 'success')

        except Exception as load_error:
            print(f"⚠️ Warning: Backfill failed: {load_error}", flush=True)
            import traceback
            traceback.print_exc()
            flash('Search preferences updated, but job loading failed. Will retry on next daily update.', 'warning')

        # Auto-trigger filtering if user has CV (with duplicate check)
        try:
            user_cvs = cv_manager.get_user_cvs(user['id'])
            if user_cvs:
                # Check if already running
                if user['id'] in matching_status and matching_status[user['id']].get('status') == 'running':
                    flash('Search preferences updated! Job matching is already in progress.', 'success')
                else:
                    # Trigger filtering in background thread
                    threading.Thread(
                        target=run_background_filtering,
                        args=(user['id'],),
                        daemon=True
                    ).start()
                    flash('Search preferences updated! Job matching started automatically. Check progress on Jobs page.', 'success')
                    return redirect(url_for('jobs'))  # Redirect to jobs page to see progress
        except Exception as filter_error:
            print(f"Error starting background filter: {filter_error}", flush=True)

    except Exception as e:
        flash(f'Error updating preferences: {str(e)}', 'error')
        print(f"Error updating search preferences: {e}", flush=True)
        import traceback
        traceback.print_exc()

    return redirect(url_for('search_preferences'))


# Global dictionary to track matching status
matching_status = {}

def run_background_filtering(user_id: int):
    """Run semantic filtering and Claude analysis in background"""
    from src.matching.matcher import run_background_matching
    run_background_matching(user_id, matching_status)


@app.route('/run-job-matching', methods=['POST'])
@login_required
def run_job_matching():
    """Manually trigger job matching for current user"""
    user_id = get_user_id()
    
    try:
        # Check if user has CV
        user_cvs = cv_manager.get_user_cvs(user_id)
        if not user_cvs:
            flash('Please upload your CV first before running job matching', 'error')
            return redirect(url_for('upload_cv'))
        
        # Check if already running
        if user_id in matching_status and matching_status[user_id].get('status') == 'running':
            flash('⏳ Job matching is already in progress! Scroll down to see the progress indicator.', 'warning')
            return redirect(url_for('jobs'))
        
        # Check if filtering is needed
        should_filter, reason = cv_manager.should_refilter(user_id)
        if not should_filter:
            flash(f'Job matching is up to date. {reason}', 'info')
            return redirect(url_for('jobs'))
        
        # Start background filtering
        threading.Thread(
            target=run_background_filtering,
            args=(user_id,),
            daemon=True
        ).start()
        
        flash('Job matching started! Progress will update automatically below.', 'success')
        return redirect(url_for('jobs'))
        
    except Exception as e:
        flash(f'Error starting job matching: {str(e)}', 'error')
        return redirect(url_for('jobs'))


@app.route('/matching-status')
@login_required
def matching_status_endpoint():
    """Get current matching status for user"""
    user_id = get_user_id()
    status = matching_status.get(user_id, {
        'status': 'idle',
        'progress': 0,
        'message': 'Not running'
    })
    return jsonify(status)


@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    return render_template('base.html'), 500


@app.route('/test-bulk-fetch')
def test_bulk_fetch():
    """Test endpoint to fetch all recent jobs at once"""
    from flask import jsonify
    from collectors.activejobs import ActiveJobsCollector
    import yaml
    
    activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')
    
    if not activejobs_key:
        return jsonify({"error": "ACTIVEJOBS_API_KEY not configured"}), 400
    
    collector = ActiveJobsCollector(activejobs_key)
    
    print("\n" + "="*60)
    print("Testing bulk fetch: All Germany jobs from last 24h")
    print("="*60)
    
    # Fetch all recent Germany jobs
    all_jobs = collector.search_all_recent_jobs(
        location="Germany",
        max_pages=10,  # Up to 1000 jobs
        date_posted="24h"
    )
    
    print(f"\nTotal jobs fetched: {len(all_jobs)}")
    print("="*60 + "\n")
    
    # Load user's keywords for filtering demo
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    keywords = config.get('search_config', {}).get('keywords', [])
    
    # Count how many match our keywords
    matching_jobs = []
    for job in all_jobs:
        title_lower = str(job.get('title', '')).lower()
        if any(str(keyword).lower() in title_lower for keyword in keywords):
            matching_jobs.append(job)
    
    # Build sample jobs list safely
    sample_jobs = []
    for j in all_jobs[:10]:
        sample_jobs.append({
            "title": str(j.get("title", "N/A")),
            "company": str(j.get("company", "N/A"))
        })
    
    requests_used = (len(all_jobs) // 100) + 1 if all_jobs else 0
    keyword_requests = len(keywords) * 9
    
    result = {
        "total_jobs_fetched": len(all_jobs),
        "api_requests_used": requests_used,
        "matching_keywords": len(matching_jobs),
        "keywords_tested": keywords,
        "sample_jobs": sample_jobs,
        "efficiency": {
            "bulk_approach": str(requests_used) + " requests for " + str(len(all_jobs)) + " jobs",
            "keyword_search_approach": str(keyword_requests) + " requests (" + str(len(keywords)) + " keywords x 9 locations)"
        }
    }
    
    return jsonify(result)


@app.route('/admin/stats')
@login_required
def admin_stats():
    """Admin stats dashboard"""
    return render_template('admin_stats.html')


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for stats data"""
    from datetime import datetime, timedelta
    import requests
    
    stats = {}
    
    # 1. JOB DATABASE STATS
    try:
        # Jobs by source
        jobs_by_source = job_db.execute_query("""
            SELECT source, COUNT(*) as count
            FROM jobs
            GROUP BY source
            ORDER BY count DESC
        """)
        stats['jobs_by_source'] = [{'source': row[0], 'count': row[1]} for row in jobs_by_source] if jobs_by_source else []
        
        # Jobs by date (last 30 days)
        jobs_by_date = job_db.execute_query("""
            SELECT DATE(discovered_date) as date, COUNT(*) as count
            FROM jobs
            WHERE discovered_date >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(discovered_date)
            ORDER BY date DESC
        """)
        stats['jobs_by_date'] = [{'date': str(row[0]), 'count': row[1]} for row in jobs_by_date] if jobs_by_date else []
        
        # Total jobs
        total_jobs = job_db.execute_query("SELECT COUNT(*) FROM jobs")
        stats['total_jobs'] = total_jobs[0][0] if total_jobs else 0
        
        # Jobs today
        jobs_today = job_db.execute_query("""
            SELECT COUNT(*) FROM jobs 
            WHERE DATE(discovered_date) = CURRENT_DATE
        """)
        stats['jobs_today'] = jobs_today[0][0] if jobs_today else 0
        
    except Exception as e:
        print(f"Error fetching job stats: {e}")
        stats['jobs_by_source'] = []
        stats['jobs_by_date'] = []
        stats['total_jobs'] = 0
        stats['jobs_today'] = 0
    
    # 2. USER ACTIVITY STATS
    try:
        # Total users
        total_users = job_db.execute_query("SELECT COUNT(*) FROM users")
        stats['total_users'] = total_users[0][0] if total_users else 0
        
        # Total CVs
        total_cvs = job_db.execute_query("SELECT COUNT(*) FROM cvs")
        stats['total_cvs'] = total_cvs[0][0] if total_cvs else 0
        
        # Total matches
        total_matches = job_db.execute_query("SELECT COUNT(*) FROM user_job_matches")
        stats['total_matches'] = total_matches[0][0] if total_matches else 0
        
        # Matches today
        matches_today = job_db.execute_query("""
            SELECT COUNT(*) FROM user_job_matches 
            WHERE DATE(matched_date) = CURRENT_DATE
        """)
        stats['matches_today'] = matches_today[0][0] if matches_today else 0
        
        # Match quality distribution
        match_distribution = job_db.execute_query("""
            SELECT 
                CASE 
                    WHEN semantic_score >= 85 THEN '85-100%'
                    WHEN semantic_score >= 70 THEN '70-84%'
                    WHEN semantic_score >= 50 THEN '50-69%'
                    ELSE '30-49%'
                END as range,
                COUNT(*) as count
            FROM user_job_matches
            WHERE semantic_score IS NOT NULL
            GROUP BY range
            ORDER BY range DESC
        """)
        stats['match_distribution'] = [{'range': row[0], 'count': row[1]} for row in match_distribution] if match_distribution else []
        
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        stats['total_users'] = 0
        stats['total_cvs'] = 0
        stats['total_matches'] = 0
        stats['matches_today'] = 0
        stats['match_distribution'] = []
    
    # 3. CLAUDE API USAGE
    try:
        # Total Claude analyses
        claude_analyses = job_db.execute_query("""
            SELECT COUNT(*) FROM user_job_matches 
            WHERE claude_score IS NOT NULL
        """)
        stats['claude_analyses_total'] = claude_analyses[0][0] if claude_analyses else 0
        
        # Claude analyses today
        claude_today = job_db.execute_query("""
            SELECT COUNT(*) FROM user_job_matches 
            WHERE claude_score IS NOT NULL 
            AND DATE(matched_date) = CURRENT_DATE
        """)
        stats['claude_analyses_today'] = claude_today[0][0] if claude_today else 0
        
        # Estimated cost (assuming $0.03 per analysis)
        stats['claude_estimated_cost'] = stats['claude_analyses_total'] * 0.03
        
    except Exception as e:
        print(f"Error fetching Claude stats: {e}")
        stats['claude_analyses_total'] = 0
        stats['claude_analyses_today'] = 0
        stats['claude_estimated_cost'] = 0
    
    # 4. TOP COMPANIES & LOCATIONS
    try:
        top_companies = job_db.execute_query("""
            SELECT company, COUNT(*) as count
            FROM jobs
            GROUP BY company
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_companies'] = [{'company': row[0], 'count': row[1]} for row in top_companies] if top_companies else []
        
        top_locations = job_db.execute_query("""
            SELECT location, COUNT(*) as count
            FROM jobs
            WHERE location IS NOT NULL AND location != ''
            GROUP BY location
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_locations'] = [{'location': row[0], 'count': row[1]} for row in top_locations] if top_locations else []
        
    except Exception as e:
        print(f"Error fetching top companies/locations: {e}")
        stats['top_companies'] = []
        stats['top_locations'] = []
    
    # 5. API QUOTA TRACKING
    stats['api_quotas'] = {}
    
    # JSearch API quota
    jsearch_key = os.getenv('JSEARCH_API_KEY')
    if jsearch_key:
        try:
            # Try to get quota info from JSearch
            response = requests.get(
                'https://jsearch.p.rapidapi.com/quota',
                headers={
                    'X-RapidAPI-Key': jsearch_key,
                    'X-RapidAPI-Host': 'jsearch.p.rapidapi.com'
                },
                timeout=5
            )
            if response.status_code == 200:
                quota_data = response.json()
                stats['api_quotas']['jsearch'] = {
                    'available': True,
                    'requests_remaining': quota_data.get('requests_remaining', 'Unknown'),
                    'requests_limit': quota_data.get('requests_limit', 'Unknown'),
                    'quota_data': quota_data
                }
            else:
                stats['api_quotas']['jsearch'] = {
                    'available': True,
                    'requests_remaining': 'Unable to fetch',
                    'requests_limit': 'Check RapidAPI dashboard',
                    'error': f"Status {response.status_code}"
                }
        except Exception as e:
            stats['api_quotas']['jsearch'] = {
                'available': True,
                'requests_remaining': 'Unable to fetch',
                'requests_limit': 'Check RapidAPI dashboard',
                'error': str(e)
            }
    else:
        stats['api_quotas']['jsearch'] = {'available': False, 'message': 'API key not configured'}
    
    # Active Jobs API quota
    activejobs_key = os.getenv('ACTIVEJOBS_API_KEY')
    if activejobs_key:
        try:
            # Try to get quota info from Active Jobs DB
            response = requests.get(
                'https://active-jobs-db.p.rapidapi.com/quota',
                headers={
                    'X-RapidAPI-Key': activejobs_key,
                    'X-RapidAPI-Host': 'active-jobs-db.p.rapidapi.com'
                },
                timeout=5
            )
            if response.status_code == 200:
                quota_data = response.json()
                stats['api_quotas']['activejobs'] = {
                    'available': True,
                    'requests_remaining': quota_data.get('requests_remaining', 'Unknown'),
                    'requests_limit': quota_data.get('requests_limit', 'Unknown'),
                    'quota_data': quota_data
                }
            else:
                stats['api_quotas']['activejobs'] = {
                    'available': True,
                    'requests_remaining': 'Unable to fetch',
                    'requests_limit': 'Check RapidAPI dashboard',
                    'error': f"Status {response.status_code}"
                }
        except Exception as e:
            stats['api_quotas']['activejobs'] = {
                'available': True,
                'requests_remaining': 'Unable to fetch',
                'requests_limit': 'Check RapidAPI dashboard',
                'error': str(e)
            }
    else:
        stats['api_quotas']['activejobs'] = {'available': False, 'message': 'API key not configured'}
    
    # Arbeitsagentur (always available, free)
    stats['api_quotas']['arbeitsagentur'] = {
        'available': True,
        'requests_remaining': 'Unlimited',
        'requests_limit': 'Unlimited (Free)',
        'message': 'Free German government API'
    }
    
    # 6. SYSTEM STATS
    stats['system'] = {
        'timestamp': datetime.now().isoformat(),
        'database': 'PostgreSQL (Railway)',
        'environment': os.getenv('FLASK_ENV', 'development')
    }
    
    return jsonify(stats)


@app.route('/admin/clear-model-cache', methods=['POST'])
@login_required
def clear_model_cache():
    """Clear cached semantic models (admin only)"""
    global _semantic_models

    user = get_user_context()[0]

    # Simple admin check - you can make this more restrictive
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        cleared_models = list(_semantic_models.keys())
        _semantic_models.clear()

        return jsonify({
            'success': True,
            'message': 'Model cache cleared successfully',
            'cleared_models': cleared_models
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ Resume Generation API Routes ============

@app.route('/api/save-competency-evidence', methods=['POST'])
@login_required
def save_competency_evidence():
    """
    Save user's claimed competencies/skills with evidence

    Request Body:
    {
        "selections": [
            {
                "name": "Agile Methodology",
                "type": "competency",
                "work_experience_ids": [1, 3],
                "evidence": "Led daily standups..."
            }
        ]
    }

    Returns:
        JSON with success status and message
    """
    if not resume_ops:
        return jsonify({
            'success': False,
            'error': 'Resume generation not available'
        }), 503

    user_id = get_user_id()
    data = request.json

    if not data or 'selections' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing selections data'
        }), 400

    try:
        selections = data.get('selections', [])

        if not selections:
            return jsonify({
                'success': False,
                'error': 'No selections provided'
            }), 400

        # Save all selections in a single transaction
        resume_ops.save_multiple_claims(user_id, selections)

        return jsonify({
            'success': True,
            'message': f'Evidence saved for {len(selections)} items'
        })

    except Exception as e:
        import traceback
        print(f"Error saving competency evidence: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate-resume/<int:job_id>', methods=['POST'])
@login_required
def generate_resume(job_id):
    """
    Generate tailored resume for a specific job

    Args:
        job_id: Job ID to generate resume for

    Returns:
        JSON with resume HTML, PDF URL, and metadata
    """
    if not resume_generator or not resume_ops:
        return jsonify({
            'success': False,
            'error': 'Resume generation not available'
        }), 503

    user_id = get_user_id()

    try:
        # Get selections from request body
        request_data = request.get_json() or {}
        selections = request_data.get('selections', [])

        # Save selections to database first (if provided)
        if selections:
            print(f"Saving {len(selections)} selections to database...")
            resume_ops.save_multiple_claims(user_id, selections)

        # Get user's CV profile
        profile = cv_manager.get_primary_profile(user_id)
        if not profile:
            return jsonify({
                'success': False,
                'error': 'No CV profile found. Please upload your CV first.'
            }), 400

        # Normalize work_history to work_experience for resume generator
        if profile and 'work_history' in profile:
            work_experiences = []
            for wh in profile.get('work_history', []):
                # Parse duration string (e.g., "Jul 2021 - Present")
                duration = wh.get('duration', '')
                parts = duration.split(' - ')
                start_date = parts[0] if parts else ''
                end_date = parts[1] if len(parts) > 1 else 'Present'

                work_experiences.append({
                    'title': wh.get('title', ''),
                    'company': wh.get('company', ''),
                    'start_date': start_date,
                    'end_date': end_date,
                    'description': wh.get('description', ''),
                    'key_achievements': wh.get('key_achievements', [])
                })
            profile['work_experience'] = work_experiences

        # Get job details
        job = job_db.get_job_by_id(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404

        # Get user's claimed competencies/skills (including newly saved)
        claimed_data = resume_ops.get_user_claimed_data(user_id)

        # Get user's contact information for resume header
        # Use resume-specific fields if set, otherwise fall back to login credentials
        user_info = None
        conn = cv_manager.connection_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT name, email, phone, resume_name, resume_email, resume_phone
                FROM users WHERE id = %s
            """, (user_id,))
            user_row = cur.fetchone()
            if user_row:
                user_info = {
                    'name': user_row[3] or user_row[0],  # resume_name or fallback to name
                    'email': user_row[4] or user_row[1],  # resume_email or fallback to email
                    'phone': user_row[5] or user_row[2]   # resume_phone or fallback to phone
                }
        finally:
            cv_manager.connection_pool.putconn(conn)

        # Generate resume HTML
        print(f"Generating resume for user {user_id}, job {job_id}...")
        resume_html = resume_generator.generate_resume_html(
            profile,
            job,
            claimed_data,
            user_info
        )

        print(f"Resume HTML generated successfully (not saved yet - waiting for user to edit and save)")

        # Return HTML without saving to database (user will edit first, then save)
        return jsonify({
            'success': True,
            'resume_html': resume_html,
            'job_title': job.get('title'),
            'company': job.get('company')
        })

    except Exception as e:
        import traceback
        print(f"Error generating resume: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/save-resume/<int:job_id>', methods=['POST'])
@login_required
def save_resume_route(job_id):
    """
    Save edited resume to database

    Args:
        job_id: Job ID the resume was generated for

    Request Body:
        {
            "resume_html": "<edited HTML>",
            "selections": [...]  # Optional - already saved during generation
        }

    Returns:
        JSON with resume_id and success status
    """
    if not resume_generator or not resume_ops:
        return jsonify({
            'success': False,
            'error': 'Resume save not available'
        }), 503

    user_id = get_user_id()

    try:
        # Get edited resume HTML from request
        request_data = request.get_json() or {}
        resume_html = request_data.get('resume_html')

        if not resume_html:
            return jsonify({
                'success': False,
                'error': 'No resume HTML provided'
            }), 400

        # Get job details to include in response
        job = job_db.get_job_by_id(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404

        # Get user's claimed competencies/skills
        claimed_data = resume_ops.get_user_claimed_data(user_id)

        # Create resumes directory if it doesn't exist
        resumes_dir = os.path.join('static', 'resumes')
        os.makedirs(resumes_dir, exist_ok=True)

        # Generate PDF from edited HTML
        pdf_filename = f"resume_user{user_id}_job{job_id}_{int(time.time())}.pdf"
        pdf_path = os.path.join(resumes_dir, pdf_filename)

        try:
            print(f"Generating PDF from edited resume at {pdf_path}...")
            resume_generator.html_to_pdf(resume_html, pdf_path)
            print(f"✅ PDF generated successfully")
        except Exception as pdf_error:
            print(f"⚠️  PDF generation failed: {pdf_error}")
            print("Continuing without PDF...")
            pdf_path = None

        # Save to database
        resume_id = resume_ops.save_generated_resume(
            user_id,
            job_id,
            resume_html,
            pdf_path,
            claimed_data
        )

        print(f"Edited resume saved successfully: ID {resume_id}")

        return jsonify({
            'success': True,
            'resume_id': resume_id,
            'pdf_url': f'/download/resume/{resume_id}' if pdf_path else None,
            'job_title': job.get('title'),
            'company': job.get('company')
        })

    except Exception as e:
        import traceback
        print(f"Error saving resume: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/update-contact-info', methods=['POST'])
@login_required
def update_contact_info():
    """
    Update user's resume contact information (separate from login credentials)

    Request Body:
        {
            "resume_name": "Full Name",  # Optional - will use login name if empty
            "resume_email": "email@example.com",  # Optional - will use login email if empty
            "resume_phone": "+1 (555) 123-4567"  # Optional
        }

    Returns:
        JSON with success status and fallback values
    """
    user_id = get_user_id()

    try:
        request_data = request.get_json() or {}
        resume_name = request_data.get('resume_name', '').strip() or None
        resume_email = request_data.get('resume_email', '').strip() or None
        resume_phone = request_data.get('resume_phone', '').strip() or None

        # Validate email format if provided
        if resume_email:
            import re
            email_regex = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
            if not email_regex.match(resume_email):
                return jsonify({
                    'success': False,
                    'error': 'Invalid email format'
                }), 400

        # Update user record with resume-specific fields
        conn = cv_manager.connection_pool.getconn()
        try:
            cur = conn.cursor()

            # Update resume contact fields
            cur.execute("""
                UPDATE users
                SET resume_name = %s, resume_email = %s, resume_phone = %s, last_updated = NOW()
                WHERE id = %s
            """, (resume_name, resume_email, resume_phone, user_id))

            # Get login credentials for fallback display
            cur.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
            user_row = cur.fetchone()

            conn.commit()
        finally:
            cv_manager.connection_pool.putconn(conn)

        fallback_name = user_row[0] if user_row else 'Not set'
        fallback_email = user_row[1] if user_row else 'Not set'

        print(f"Updated resume contact info for user {user_id}:")
        print(f"  Resume Name: {resume_name or f'(using login: {fallback_name})'}")
        print(f"  Resume Email: {resume_email or f'(using login: {fallback_email})'}")
        print(f"  Resume Phone: {resume_phone or '(not set)'}")

        return jsonify({
            'success': True,
            'message': 'Resume contact information updated successfully',
            'fallback_name': fallback_name,
            'fallback_email': fallback_email
        })

    except Exception as e:
        import traceback
        print(f"Error updating contact info: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/download/resume/<int:resume_id>')
@login_required
def download_resume(resume_id):
    """
    Download generated resume (HTML or PDF)

    Args:
        resume_id: Resume ID to download

    Query Parameters:
        format: 'html' or 'pdf' (default: 'pdf')

    Returns:
        File download or error
    """
    if not resume_ops:
        flash('Resume download not available', 'error')
        return redirect(url_for('jobs'))

    user_id = get_user_id()
    download_format = request.args.get('format', 'pdf')

    try:
        # Get resume with user verification
        resume = resume_ops.get_resume_by_id(resume_id, user_id)

        if not resume:
            flash('Resume not found', 'error')
            return redirect(url_for('jobs'))

        job_id = resume['job_id']

        if download_format == 'html':
            # Download as HTML
            from flask import make_response

            response = make_response(resume['resume_html'])
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="resume_job_{job_id}.html"'
            return response

        elif download_format == 'pdf':
            # Download as PDF (if generated)
            pdf_path = resume.get('resume_pdf_path')

            if not pdf_path or not os.path.exists(pdf_path):
                # PDF not generated yet - offer HTML as fallback
                flash('PDF not available. Downloading HTML version instead.', 'info')
                from flask import make_response

                response = make_response(resume['resume_html'])
                response.headers['Content-Type'] = 'text/html; charset=utf-8'
                response.headers['Content-Disposition'] = f'attachment; filename="resume_job_{job_id}.html"'
                return response

            # Send PDF file
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"resume_job_{job_id}.pdf"
            )

        else:
            flash('Invalid format. Use "html" or "pdf"', 'error')
            return redirect(url_for('jobs'))

    except Exception as e:
        import traceback
        print(f"Error downloading resume: {e}")
        print(traceback.format_exc())
        flash(f'Error downloading resume: {str(e)}', 'error')
        return redirect(url_for('jobs'))


if __name__ == '__main__':
    print("="*60)
    print("🤖 Job Monitor Web UI")
    print("="*60)
    print(f"Starting server at http://localhost:8080")
    print(f"User email: {os.getenv('USER_EMAIL') or 'default@localhost'}")
    print()
    print("Available routes:")
    print("  / - Home")
    print("  /upload - Upload CV")
    print("  /profile - View Profile")
    print("  /jobs - Browse Jobs")
    print("  /dashboard - Application Dashboard")
    print()
    print("Press Ctrl+C to stop")
    print("="*60)

    # Use environment variables for production
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(debug=debug, host='0.0.0.0', port=port)
