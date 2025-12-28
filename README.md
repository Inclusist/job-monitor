# Inclusist - Job Monitoring System

An intelligent job search platform that monitors multiple job boards, analyzes matches using Claude AI, and helps you find the perfect opportunities.

## Features

- 🔍 **Multi-Source Job Search**: Indeed API, LinkedIn (email monitoring), and optional StepStone
- 🤖 **AI-Powered Analysis**: Uses Claude API to score and analyze job matches
- 📊 **Smart Prioritization**: Automatically categorizes jobs as High/Medium/Low priority
- 📄 **CV Management**: Upload and parse CVs (PDF/DOCX/TXT) with AI extraction
- 👥 **Multi-User Support**: Manage CVs and job searches for multiple users
- 📧 **Daily Digests**: Email summaries of new opportunities
- 💾 **Job Tracking**: SQLite database to track applications and status
- 🎯 **Customizable**: Configure search terms, locations, and preferences

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- Internet connection
- API keys (see Setup section)

### 2. Installation

```bash
# Clone or download the project
cd job-monitor

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Migration (Existing Users Only)

**If you're upgrading from a previous version**, run the migration script:

```bash
python scripts/migrate_to_multiuser.py
```

This will:
- Backup your existing database
- Add multi-user support
- Create a default user from your config.yaml
- Link existing jobs to your user account

**New users can skip this step** - the system will set up automatically.

### 4. Configuration

#### A. Get API Keys

**Indeed Publisher API** (Free):
1. Go to https://www.indeed.com/publisher
2. Sign up for a publisher account
3. Get your Publisher ID

**Anthropic Claude API**:
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Create an API key
4. Note: You get $5 free credits to start!

#### B. Set Up Environment

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your API keys
nano .env  # or use any text editor
```

Update these values in `.env`:
```
INDEED_PUBLISHER_ID=your_publisher_id_here
ANTHROPIC_API_KEY=your_claude_api_key_here
EMAIL_ADDRESS=your_email@gmail.com
RECIPIENT_EMAIL=reachprabhushankar@gmail.com
```

#### C. Customize Search Terms

Edit `config.yaml` to customize:
- Job titles to search for
- Locations
- Your profile information
- Preferences

### 5. Upload Your CV (Recommended)

For better job matching, upload your CV:

```bash
# Upload your CV (PDF, DOCX, or TXT)
python scripts/cv_cli.py upload --email your@email.com --file ~/path/to/your_cv.pdf
```

The system will:
- Extract text from your CV
- Use Claude AI to parse skills, experience, and education
- Store structured profile data
- Use it for more accurate job matching

Cost: ~$0.02 per CV upload (one-time)

### 6. Test the System

```bash
# Test database
python src/database/operations.py

# Test Indeed API
python src/collectors/indeed.py

# Test Claude analyzer (requires API key)
python src/analysis/claude_analyzer.py

# Run the full system
python main.py
```

### 7. Schedule Daily Runs

#### On Linux/Mac (using cron):

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 8 AM):
0 8 * * * cd /path/to/job-monitor && /path/to/job-monitor/venv/bin/python main.py
```

#### On Windows (using Task Scheduler):

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 8:00 AM
4. Action: Start a program
5. Program: `C:\path\to\job-monitor\venv\Scripts\python.exe`
6. Arguments: `C:\path\to\job-monitor\main.py`
7. Start in: `C:\path\to\job-monitor`

## Project Structure

```
job-monitor/
├── main.py                 # Main orchestration script
├── requirements.txt        # Python dependencies
├── config.yaml            # Search configuration
├── .env                   # API keys (create from .env.template)
├── README.md
│
├── src/
│   ├── collectors/        # Job collection modules
│   │   ├── indeed.py      # Indeed API integration
│   │   └── linkedin.py    # LinkedIn email monitoring (TODO)
│   │
│   ├── analysis/          # Job analysis
│   │   └── claude_analyzer.py  # Claude AI integration
│   │
│   ├── database/          # Database operations
│   │   └── operations.py  # SQLite CRUD operations
│   │
│   ├── notifications/     # Email notifications (TODO)
│   │   └── email_sender.py
│   │
│   └── utils/            # Utility functions
│       └── helpers.py
│
└── data/
    ├── jobs.db           # SQLite database (created automatically)
    └── logs/             # Log files
```

## CV Management

### Upload a CV

```bash
# Upload your CV and set as primary
python scripts/cv_cli.py upload --email your@email.com --file ~/cv.pdf

# Upload without setting as primary
python scripts/cv_cli.py upload --email your@email.com --file ~/cv.pdf --no-primary

# Skip confirmation prompt
python scripts/cv_cli.py upload --email your@email.com --file ~/cv.pdf -y
```

**Supported formats:** PDF, DOCX, TXT
**Max file size:** 10MB
**Cost:** ~$0.02 per upload (Claude AI parsing)

### List Your CVs

```bash
python scripts/cv_cli.py list --email your@email.com
```

Shows all uploaded CVs with:
- CV ID and filename
- Upload date
- File size
- Primary status
- Version number

### View Extracted Profile

```bash
# Show profile summary
python scripts/cv_cli.py show-profile --email your@email.com

# Show full profile JSON
python scripts/cv_cli.py show-profile --email your@email.com --full
```

Displays:
- Expertise summary
- Technical and soft skills
- Work experience
- Education
- Languages
- Career highlights

### Switch Primary CV

```bash
python scripts/cv_cli.py set-primary --email your@email.com --cv-id 3
```

The primary CV is used for job matching in `main.py`.

### Delete a CV

```bash
# Delete CV (with confirmation)
python scripts/cv_cli.py delete --email your@email.com --cv-id 2

# Delete without confirmation
python scripts/cv_cli.py delete --email your@email.com --cv-id 2 -y

# Keep files on disk (only delete from database)
python scripts/cv_cli.py delete --email your@email.com --cv-id 2 --keep-files
```

### Reparse a CV

If you improve the CV parsing prompt, reparse existing CVs:

```bash
python scripts/cv_cli.py reparse --cv-id 3
```

### View Statistics

```bash
# Global statistics
python scripts/cv_cli.py stats

# User-specific statistics
python scripts/cv_cli.py stats --email your@email.com
```

## Usage

### Set Your Email (Optional)

Add to `.env` file:
```
USER_EMAIL=your@email.com
```

Or set as environment variable:
```bash
export USER_EMAIL=your@email.com
```

If not set, uses email from config.yaml or defaults to `default@localhost`.

### Manual Run

```bash
python main.py
```

This will:
1. Load your user profile (from CV if uploaded, otherwise config.yaml)
2. Search Indeed for jobs matching your criteria
3. Filter out jobs already in database
4. Analyze new jobs with Claude AI using your profile
5. Store results in database with user association
6. Display high-priority matches
7. (Future: Send email digest)

### Check Database

```bash
# Install sqlite3 command line tool if needed
sqlite3 data/jobs.db

# View all jobs
SELECT title, company, match_score, priority FROM jobs ORDER BY match_score DESC;

# View high-priority jobs
SELECT title, company, match_score FROM jobs WHERE priority = 'high';

# Count by status
SELECT status, COUNT(*) FROM jobs GROUP BY status;
```

### View Logs

```bash
tail -f data/logs/job_monitor.log
```

## Configuration Reference

### Search Keywords (`config.yaml`)

Customize the job titles you're searching for:
```yaml
search_config:
  keywords:
    - "Head of Data Science"
    - "AI Team Lead"
    # Add more...
```

### Match Score Thresholds

Adjust in `config.yaml`:
```yaml
preferences:
  min_match_score: 60          # Minimum to include
  high_priority_threshold: 85  # Threshold for high priority
```

### Claude Model Selection

In `main.py`, you can change the model:
```python
# Cost-effective (recommended)
analyzer = ClaudeJobAnalyzer(api_key, model="claude-3-5-haiku-20241022")

# Higher quality (more expensive)
analyzer = ClaudeJobAnalyzer(api_key, model="claude-sonnet-4-20250514")
```

## Cost Estimates

### Base System:
- Indeed API: **Free**
- Claude API (Haiku for job matching): **~$1.50/month**
- CV Upload (Sonnet, one-time): **~$0.02 per CV**
- Total ongoing: **~$1.50/month**

### With Optional Features:
- StepStone via Apify: **€15/month**
- Multiple CV versions: **~$0.02 per upload**

### Cost Breakdown:
- **Job Analysis**: ~50 jobs/day × $0.001 = $1.50/month (Haiku)
- **CV Parsing**: One-time $0.02 per CV (Sonnet)
- **Re-parsing**: Only when you explicitly request it

## Troubleshooting

### "INDEED_PUBLISHER_ID not configured"
- Make sure you've copied `.env.template` to `.env`
- Sign up at https://www.indeed.com/publisher
- Add your Publisher ID to `.env`

### "ANTHROPIC_API_KEY not configured"
- Get API key from https://console.anthropic.com/
- Add it to `.env` file

### "No jobs found"
- Check your search terms in `config.yaml`
- Try broader keywords
- Increase `days_back` parameter in `main.py`

### Database errors
- Delete `data/jobs.db` to start fresh
- Run `python src/database/operations.py` to test

### Import errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt`

## How CV Parsing Works

1. **Upload**: You upload a CV file (PDF, DOCX, or TXT)
2. **Text Extraction**: The system extracts raw text using specialized parsers
3. **AI Analysis**: Claude AI parses the text into structured data:
   - Technical skills (Python, SQL, AWS, etc.)
   - Soft skills (Leadership, Communication, etc.)
   - Work experience with achievements
   - Education and certifications
   - Languages with proficiency levels
   - Career highlights and expertise summary
4. **Storage**: Structured data saved to database
5. **Job Matching**: Profile used for more accurate job scoring

### Profile vs CV

- **config.yaml profile**: Manual, simple, works immediately
- **CV profile**: Automatic extraction, more detailed, better matching
- **Fallback**: System uses config.yaml if no CV uploaded
- **Recommendation**: Upload CV for best results

## Multi-User Features

The system now supports multiple users:

- Each user identified by email
- Each user can have multiple CVs
- One CV marked as "primary" for job matching
- Jobs linked to users in database
- Separate CV storage per user

**Single user?** Just use one email consistently. The system handles it seamlessly.

## Future Enhancements

**Completed:**
- [x] Multi-user support
- [x] CV upload and parsing
- [x] AI-powered profile extraction
- [x] CV version management

**Planned:**
- [ ] LinkedIn email monitoring
- [ ] StepStone integration via Apify
- [ ] Email digest with HTML formatting
- [ ] Cover letter auto-generation from CV + job
- [ ] Application tracking
- [ ] Web dashboard
- [ ] Slack/Telegram notifications
- [ ] Company career page monitoring
- [ ] Multi-language CV support
- [ ] CV quality scoring
- [ ] Skill gap analysis

## Support

For issues or questions:
1. Check logs in `data/logs/job_monitor.log`
2. Review configuration in `config.yaml` and `.env`
3. Test individual components using their test functions

## License

MIT License - feel free to modify and use for your own job search!

---

**Good luck with your job search!** 🚀
