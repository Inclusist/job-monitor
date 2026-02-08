# Daily Job Updater - Setup Guide

This automated workflow fetches fresh jobs daily based on your users' search preferences.

## How It Works

1. **Collects User Preferences** - Reads `search_keywords` and `search_locations` from all active users
2. **Smart Aggregation** - Combines similar searches to avoid duplicate API calls
3. **Fetches Fresh Jobs** - Queries Arbeitsagentur API for jobs posted in last 1-2 days
4. **Deduplication** - Skips jobs already in database
5. **Updates Database** - Adds only new, relevant jobs

## Quick Start

```bash
# Test with dry run (see what would happen without saving)
python scripts/daily_job_updater.py --dry-run

# Fetch jobs from last 24 hours (default)
python scripts/daily_job_updater.py

# Fetch jobs from last 2 days
python scripts/daily_job_updater.py --days 2

# Use default searches if no user preferences exist yet
python scripts/daily_job_updater.py --use-defaults

# Verbose output
python scripts/daily_job_updater.py --verbose
```

## Setting Up User Search Preferences

Users can set their preferences via the web UI at `/search-preferences`, or you can set them programmatically:

```python
from src.database.postgres_operations import PostgreSQLDatabase
from src.database.postgres_cv_operations import PostgreSQLCVManager

db = PostgreSQLDatabase()
cv_manager = PostgreSQLCVManager(db.conn_pool)

# Set search preferences for a user
cv_manager.update_user_search_preferences(
    user_id=1,
    keywords=['Python Developer', 'Software Engineer', 'Data Scientist'],
    locations=['Berlin', 'München', 'Hamburg']
)
```

## Scheduling Daily Updates

### Option 1: Cron (Linux/macOS)

Edit crontab:
```bash
crontab -e
```

Add this line to run daily at 6 AM:
```cron
0 6 * * * cd /Users/prabhu.ramachandran/job-monitor && python3 scripts/daily_job_updater.py >> data/logs/daily_updater.log 2>&1
```

Verify cron job:
```bash
crontab -l
```

### Option 2: macOS LaunchAgent

Create file: `~/Library/LaunchAgents/com.jobmonitor.dailyupdater.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jobmonitor.dailyupdater</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/prabhu.ramachandran/job-monitor/scripts/daily_job_updater.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/prabhu.ramachandran/job-monitor</string>
    
    <key>StandardOutPath</key>
    <string>/Users/prabhu.ramachandran/job-monitor/data/logs/daily_updater.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/prabhu.ramachandran/job-monitor/data/logs/daily_updater_error.log</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Load the agent:
```bash
launchctl load ~/Library/LaunchAgents/com.jobmonitor.dailyupdater.plist
launchctl start com.jobmonitor.dailyupdater  # Test immediately
launchctl list | grep jobmonitor  # Verify it's loaded
```

Unload if needed:
```bash
launchctl unload ~/Library/LaunchAgents/com.jobmonitor.dailyupdater.plist
```

### Option 3: systemd (Linux)

Create service: `/etc/systemd/system/jobmonitor-daily-update.service`

```ini
[Unit]
Description=Job Monitor Daily Updater
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/job-monitor
ExecStart=/usr/bin/python3 /path/to/job-monitor/scripts/daily_job_updater.py
StandardOutput=append:/path/to/job-monitor/data/logs/daily_updater.log
StandardError=append:/path/to/job-monitor/data/logs/daily_updater_error.log

[Install]
WantedBy=multi-user.target
```

Create timer: `/etc/systemd/system/jobmonitor-daily-update.timer`

```ini
[Unit]
Description=Run Job Monitor Daily Updater at 6 AM

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jobmonitor-daily-update.timer
sudo systemctl start jobmonitor-daily-update.timer
sudo systemctl status jobmonitor-daily-update.timer
```

### Option 4: Railway Cron (Production)

Add to your Railway service:

1. Go to Railway dashboard → Your service → Settings
2. Add Environment Variable:
   ```
   RAILWAY_CRON_SCHEDULE=0 6 * * *
   ```
3. Add cron command to your deployment:
   ```bash
   # In your Procfile or start script
   python scripts/daily_job_updater.py
   ```

## Example Output

```
================================================================================
SMART DAILY JOB UPDATER - Starting
================================================================================
Mode: LIVE UPDATE
Fetching jobs from last 1 day(s)

Step 1: Collecting user search preferences...
Found 5 users with search preferences
  - user1@example.com: 3 keywords, 2 locations
  - user2@example.com: 2 keywords, 3 locations
  ... and 3 more users

Step 2: Aggregating unique search queries...
Aggregated searches: 8 keywords × 7 locations
Unique search queries: 56

Step 3: Fetching fresh jobs (last 1 day(s))...
[Query 1/56] Searching: keyword='Python Developer', location='Berlin'
  → Found 15 jobs
[Query 2/56] Searching: keyword='Python Developer', location='München'
  → Found 8 jobs
...

Step 4: Saving jobs to database...
Total jobs fetched: 234
Saved 127 new jobs

================================================================================
DAILY JOB UPDATE SUMMARY
================================================================================
Mode: LIVE UPDATE
Duration: 0:02:34
Users analyzed: 5
Unique search queries: 56
Total jobs fetched: 234
New jobs saved: 127
Duplicates skipped: 107
Errors: 0
New job rate: 54.3%
================================================================================
```

## Performance Optimization

### Rate Limiting
The script includes 0.5s delays between API calls to be respectful to the Arbeitsagentur API.

### Smart Deduplication
- Tracks job IDs in-memory during execution
- Checks database before inserting
- Skips jobs already processed

### Query Optimization
- Combines user preferences to minimize API calls
- Uses `days_since_posted=1` by default (only fresh jobs)
- Limits to 100 jobs per query

## Monitoring

### Check Logs
```bash
# View recent updates
tail -f data/logs/daily_updater.log

# Check for errors
grep ERROR data/logs/daily_updater.log
```

### Database Stats
```sql
-- Jobs added today
SELECT COUNT(*) FROM jobs 
WHERE date_posted >= CURRENT_DATE;

-- Jobs by source and date
SELECT source, DATE(date_posted) as day, COUNT(*) 
FROM jobs 
WHERE date_posted >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY source, day 
ORDER BY day DESC, source;
```

## Troubleshooting

### No User Preferences
If no users have set preferences, the script will warn you. Options:
1. Use `--use-defaults` flag for fallback searches
2. Add user preferences via web UI or programmatically
3. Modify default searches in the script

### Too Many/Few Jobs
Adjust the `days_since_posted` parameter:
- `--days 1` (default): Only today's jobs (~50-200 jobs)
- `--days 2`: Last 2 days (~100-400 jobs)
- `--days 7`: Last week (~500-2000 jobs)

### API Rate Limits
The Bundesagentur API is public and has no strict rate limits, but be respectful:
- Default 0.5s delay between queries
- Max 100 jobs per query
- ~1-2 minutes for 50 queries

## Extending to Other Sources

To add Indeed, JSearch, or other collectors:

```python
# In daily_job_updater.py
from src.collectors.indeed import IndeedCollector
from src.collectors.jsearch import JSearchCollector

class SmartJobUpdater:
    def __init__(self, ...):
        self.collectors = [
            ArbeitsagenturCollector(),
            IndeedCollector(),
            JSearchCollector()
        ]
    
    def fetch_jobs_for_query(self, keyword, location, days):
        all_jobs = []
        for collector in self.collectors:
            jobs = collector.search_and_parse(...)
            all_jobs.extend(jobs)
        return all_jobs
```

## Best Practices

1. **Start with dry run** - Test with `--dry-run` first
2. **Monitor logs** - Check for errors and duplicate rates
3. **Adjust frequency** - Daily at 6 AM captures overnight postings
4. **Set user preferences** - Encourage users to set search keywords
5. **Check duplicate rate** - Should be 40-60% after first week
6. **Database cleanup** - Periodically remove old jobs (90+ days)

## Next Steps

1. Test the script with dry run
2. Add your search preferences
3. Run once manually to populate initial data
4. Set up cron/scheduler for daily runs
5. Monitor logs for a few days
6. Adjust parameters as needed
