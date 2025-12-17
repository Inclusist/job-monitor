#!/usr/bin/env python3
"""
Flask Web Application for Job Monitor
Simple web UI for CV management and job viewing
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.operations import JobDatabase
from database.cv_operations import CVManager
from parsers.cv_parser import CVParser
from analysis.cv_analyzer import CVAnalyzer
from cv.cv_handler import CVHandler

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize components
db_path = os.getenv('DATABASE_PATH', 'data/jobs.db')
cv_manager = CVManager(db_path)
job_db = JobDatabase(db_path)
parser = CVParser()

# Initialize CV analyzer
anthropic_key = os.getenv('ANTHROPIC_API_KEY')
if not anthropic_key:
    print("Warning: ANTHROPIC_API_KEY not set. CV upload will not work.")
    analyzer = None
else:
    analyzer = CVAnalyzer(anthropic_key)

handler = CVHandler(cv_manager, parser, analyzer, storage_root='data/cvs') if analyzer else None


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_email():
    """Get user email from session or env"""
    return session.get('user_email') or os.getenv('USER_EMAIL') or 'default@localhost'


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
        'total_cvs': user_stats.get('total_cvs', 0),
        'primary_cv_name': user_stats.get('primary_cv_name'),
        'total_jobs': job_stats.get('total_jobs', 0),
        'high_priority': job_stats.get('by_priority', {}).get('high', 0)
    }

    return user, stats


@app.route('/')
def index():
    """Home page"""
    user, stats = get_user_context()
    return render_template('index.html', user=user, stats=stats)


@app.route('/upload', methods=['GET', 'POST'])
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
def view_profile():
    """View CV profile"""
    user, stats = get_user_context()

    # Get primary CV and profile
    cv = cv_manager.get_primary_cv(user['id'])

    if not cv:
        return render_template('profile.html', user=user, profile=None, cv=None)

    profile = cv_manager.get_cv_profile(cv['id'])

    # Parse JSON fields
    if profile:
        json_fields = ['technical_skills', 'soft_skills', 'languages', 'certifications',
                      'work_experience', 'leadership_experience', 'education',
                      'career_highlights', 'industries']

        for field in json_fields:
            if field in profile and isinstance(profile[field], str):
                try:
                    profile[field] = json.loads(profile[field])
                except:
                    profile[field] = []

    return render_template('profile.html', user=user, profile=profile, cv=cv)


@app.route('/jobs')
def jobs():
    """Jobs dashboard"""
    user, stats = get_user_context()

    # Get filter parameters
    priority = request.args.get('priority', '')
    min_score = request.args.get('min_score', type=int)

    # Get jobs for user
    if priority:
        jobs_list = job_db.get_jobs_by_priority(priority)
    elif min_score:
        jobs_list = job_db.get_jobs_by_score(min_score)
    else:
        # Get all jobs (limit to recent 50)
        jobs_list = job_db.get_jobs_by_score(0, max_results=50)

    # Parse JSON fields
    for job in jobs_list:
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

    return render_template('jobs.html', user=user, stats=stats, jobs=jobs_list,
                          priority=priority, min_score=min_score)


@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    """Job detail page"""
    # Get job from database
    # This is a simplified version - you'd implement a get_job_by_id method
    jobs_list = job_db.get_jobs_by_score(0, max_results=1000)
    job = next((j for j in jobs_list if j['id'] == job_id), None)

    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('jobs'))

    # Parse JSON fields
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

    return render_template('job_detail.html', job=job)


@app.route('/jobs/<int:job_id>/status/<status>')
def update_job_status(job_id, status):
    """Update job status"""
    try:
        # Get job to verify it exists
        jobs_list = job_db.get_jobs_by_score(0, max_results=1000)
        job = next((j for j in jobs_list if j['id'] == job_id), None)

        if job:
            job_db.update_job_status(job['job_id'], status)
            flash(f'Job marked as {status}', 'success')
        else:
            flash('Job not found', 'error')
    except Exception as e:
        flash(f'Error updating job: {str(e)}', 'error')

    return redirect(url_for('jobs'))


@app.route('/run-search')
def run_search():
    """Run new job search (placeholder)"""
    flash('Job search feature coming soon! Use main.py to run searches for now.', 'info')
    return redirect(url_for('jobs'))


@app.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return render_template('base.html'), 404


@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    return render_template('base.html'), 500


if __name__ == '__main__':
    print("="*60)
    print("🤖 Job Monitor Web UI")
    print("="*60)
    print(f"Starting server at http://localhost:5000")
    print(f"User email: {get_user_email()}")
    print()
    print("Available routes:")
    print("  / - Home")
    print("  /upload - Upload CV")
    print("  /profile - View Profile")
    print("  /jobs - Browse Jobs")
    print()
    print("Press Ctrl+C to stop")
    print("="*60)

    app.run(debug=True, host='0.0.0.0', port=5000)
