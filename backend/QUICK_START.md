# Job Monitoring System - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Download and Extract
You should have downloaded the `job-monitor` folder. Extract it to your preferred location.

### Step 2: Install Python Dependencies

Open terminal/command prompt in the project folder:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Get Your API Keys

#### Indeed Publisher API (Free)
1. Go to: https://www.indeed.com/publisher
2. Click "Sign up" or "Register"
3. Fill out the form (you can use your personal email)
4. Once registered, you'll get your Publisher ID (looks like: 1234567890123456)
5. Save this number - you'll need it in the next step

#### Anthropic Claude API
1. Go to: https://console.anthropic.com/
2. Sign up or log in
3. Go to "API Keys" section
4. Click "Create Key"
5. Copy the key (starts with "sk-ant-...")
6. **Important**: You get $5 free credits to start!

### Step 4: Configure the System

```bash
# Create your environment file
cp .env.template .env

# Edit .env file (use any text editor)
# On Mac/Linux:
nano .env
# On Windows:
notepad .env
```

Update these lines in `.env`:
```
INDEED_PUBLISHER_ID=your_publisher_id_from_indeed
ANTHROPIC_API_KEY=sk-ant-your_key_from_anthropic
RECIPIENT_EMAIL=reachprabhushankar@gmail.com
```

Save and close the file.

### Step 5: Customize Your Search

Edit `config.yaml` to customize:
- Job titles you're looking for
- Locations
- Your profile information

The default settings are already configured for your profile, but feel free to adjust!

### Step 6: Test the System

```bash
# Run the setup/test script
python setup.py
```

This will verify:
- ✅ Python version
- ✅ Dependencies installed
- ✅ API keys configured
- ✅ Database working
- ✅ Indeed API working
- ✅ Claude API working

If all tests pass, you're ready to go!

### Step 7: Run Your First Job Search

```bash
python main.py
```

This will:
1. Search Indeed for jobs matching your criteria
2. Analyze each job with Claude AI
3. Store results in the database
4. Show you high-priority matches

Check the output in your terminal and in `data/logs/job_monitor.log`

---

## 📊 What Happens During a Run?

The system will:
1. Search Indeed for combinations of your keywords + locations
2. Find jobs posted in the last 24 hours
3. Filter out jobs you've already seen
4. Send each new job to Claude for analysis
5. Claude scores each job 0-100 based on your profile
6. Store everything in a SQLite database
7. Show you the top matches

Example output:
```
🔥 HIGH PRIORITY JOBS:

1. Head of AI at Volkswagen Group Innovation
   Score: 95 | Location: Wolfsburg, Germany
   Reasoning: Perfect location match, LLM experience aligns, 
   international team leadership matches requirements...
   URL: https://...

2. AI Team Lead at AUTO1 Group
   Score: 92 | Location: Berlin/Remote
   ...
```

---

## 💰 Cost Tracking

Your first month will likely be **FREE** thanks to:
- Indeed API: Free
- Claude API: $5 free credits (covers ~1-2 months)

After free credits:
- Expected cost: **$1-3/month** for 15-30 jobs/day

You can check your Claude API usage at: https://console.anthropic.com/

---

## 🔄 Setting Up Daily Automation

Once you're happy with the results, set it to run automatically every morning:

### On Mac/Linux (using cron):
```bash
# Edit crontab
crontab -e

# Add this line (runs at 8 AM daily):
0 8 * * * cd /full/path/to/job-monitor && /full/path/to/job-monitor/venv/bin/python main.py
```

### On Windows (Task Scheduler):
1. Open Task Scheduler
2. Create Basic Task → "Job Monitor"
3. Trigger: Daily at 8:00 AM
4. Action: Start a program
   - Program: `C:\path\to\job-monitor\venv\Scripts\python.exe`
   - Arguments: `C:\path\to\job-monitor\main.py`
   - Start in: `C:\path\to\job-monitor`

---

## 🎯 Next Steps

### Check Your Database
```bash
# View jobs in database
sqlite3 data/jobs.db "SELECT title, company, match_score FROM jobs ORDER BY match_score DESC LIMIT 10;"
```

### Adjust Sensitivity
Edit `config.yaml`:
```yaml
preferences:
  min_match_score: 60  # Lower = more jobs, higher = fewer but better matches
  high_priority_threshold: 85
```

### Add More Sources
Phase 2 (coming soon):
- LinkedIn email monitoring
- StepStone via Apify (~€15/month)
- Company career pages

### Future Features
- Email digests (HTML formatted)
- Cover letter auto-generation
- Application tracking
- Web dashboard

---

## ❓ Troubleshooting

### "INDEED_PUBLISHER_ID not configured"
- Make sure you copied `.env.template` to `.env`
- Add your Publisher ID to `.env`

### "No jobs found"
- Try broader search terms in `config.yaml`
- Increase the date range (in `main.py`, change `days_back=1` to `days_back=7`)

### Database errors
- Delete `data/jobs.db` to start fresh
- Run `python src/database/operations.py` to test

### Claude API errors
- Check your API key in `.env`
- Verify you have credits at https://console.anthropic.com/
- Check if you're hitting rate limits (unlikely for personal use)

---

## 📞 Support

Issues? Check:
1. Logs in `data/logs/job_monitor.log`
2. Run `python setup.py` to diagnose
3. Review `README.md` for detailed documentation

---

## 🎉 You're All Set!

Run `python main.py` whenever you want to search for jobs, or set up automation to do it for you every morning!

Good luck with your job search! 🚀
