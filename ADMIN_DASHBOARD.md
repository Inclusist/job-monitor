# 📊 Admin Dashboard Documentation

## Overview

The Admin Dashboard provides comprehensive real-time monitoring and statistics for the Job Monitor application, including:
- Job database statistics
- User activity metrics
- API quota tracking for RapidAPI services (JSearch, Active Jobs)
- Matching performance analytics
- Real-time visualizations

## Access

**URL**: `http://localhost:8080/admin/stats`

**Authentication**: Requires login (uses Flask-Login `@login_required` decorator)

**Navigation**: Available in the top navigation bar with a "📊 Stats" link (highlighted in gold)

## Features

### 1. Key Metrics Dashboard

Four primary metric cards showing:

- **Total Jobs**: Number of jobs in database with today's additions
- **Total Matches**: User job matches created with today's count
- **Users**: Total registered users and CVs uploaded
- **Claude Analyses**: Total AI analyses performed with estimated cost

### 2. API Quota Tracking

Real-time monitoring of API usage for all job collectors:

#### JSearch API (RapidAPI)
- **Status**: Active/Inactive/Unable to fetch
- **Remaining Requests**: Current quota remaining
- **Request Limit**: Total monthly/daily limit
- **Card Color**: 
  - Blue border: Active and healthy
  - Orange border: Warning (unable to fetch quota)
  - Red border: Error (not configured)

#### Active Jobs DB (RapidAPI)
- Same metrics as JSearch
- Free tier: 5,000 jobs/month, 200 requests/month
- Tracks usage to prevent quota exhaustion

#### Arbeitsagentur (German Federal Employment Agency)
- **Status**: Always active (free API)
- **Quota**: Unlimited (∞)
- **Card Color**: Green border (unlimited)
- No usage restrictions

**Note**: If quota data cannot be fetched from RapidAPI, the dashboard displays "Unable to fetch - Check RapidAPI dashboard for details"

### 3. Jobs by Source Chart

**Type**: Doughnut Chart

**Data**: Distribution of jobs across all sources
- Shows which collectors contribute most jobs
- Color-coded for easy identification
- Interactive legend on the right

**Sources tracked**:
- Active Jobs DB
- JSearch (LinkedIn, Indeed, Google Jobs aggregated)
- Arbeitsagentur
- Direct collectors (Indeed, Stepstone, etc.)
- Test data

### 4. Match Quality Distribution

**Type**: Bar Chart

**Data**: Distribution of job matches by semantic score
- **85-100%**: Excellent matches (green)
- **70-84%**: Good matches (blue)
- **50-69%**: Fair matches (orange)
- **30-49%**: Low matches (red)

**Insights**: Shows quality of matching algorithm performance

### 5. Jobs Timeline (Last 30 Days)

**Type**: Line Chart

**Data**: Jobs discovered per day over the last 30 days
- Shows job collection trends
- Identifies peak collection days
- Helps monitor daily update performance

**Features**:
- Smooth curve (tension: 0.4)
- Filled gradient area
- Zero baseline for easy reading

### 6. Top Companies

**Type**: Ranked List

**Data**: Top 10 companies with most job postings
- Numbered rankings (1-10)
- Company name
- Job count badge

**Use Cases**:
- Identify most active hirers
- Focus matching efforts on high-volume companies
- Understand market trends

### 7. Top Locations

**Type**: Ranked List

**Data**: Top 10 locations with most job postings
- Numbered rankings (1-10)
- Location name
- Job count badge

**Use Cases**:
- Geographic distribution analysis
- Location preference recommendations
- Market concentration insights

## API Endpoints

### `/admin/stats` (HTML)
- **Method**: GET
- **Authentication**: Required
- **Returns**: Full HTML dashboard page
- **Description**: User-facing dashboard with all visualizations

### `/api/stats` (JSON)
- **Method**: GET
- **Authentication**: Required
- **Returns**: JSON object with all statistics
- **Description**: RESTful endpoint for programmatic access

**Response Structure**:
```json
{
  "total_jobs": 2267,
  "jobs_today": 12,
  "jobs_by_source": [
    {"source": "activejobs", "count": 1500},
    {"source": "jsearch", "count": 500}
  ],
  "jobs_by_date": [
    {"date": "2024-01-15", "count": 25}
  ],
  "total_users": 15,
  "total_cvs": 18,
  "total_matches": 5432,
  "matches_today": 123,
  "match_distribution": [
    {"range": "85-100%", "count": 450},
    {"range": "70-84%", "count": 1200}
  ],
  "claude_analyses_total": 234,
  "claude_analyses_today": 11,
  "claude_estimated_cost": 7.02,
  "top_companies": [
    {"company": "HelloFresh", "count": 45}
  ],
  "top_locations": [
    {"location": "Berlin, Germany", "count": 250}
  ],
  "api_quotas": {
    "jsearch": {
      "available": true,
      "requests_remaining": 450,
      "requests_limit": 1000
    },
    "activejobs": {
      "available": true,
      "requests_remaining": 150,
      "requests_limit": 200
    },
    "arbeitsagentur": {
      "available": true,
      "requests_remaining": "Unlimited",
      "requests_limit": "Unlimited (Free)"
    }
  },
  "system": {
    "timestamp": "2024-01-15T14:30:00.000Z",
    "database": "PostgreSQL (Railway)",
    "environment": "development"
  }
}
```

## Database Queries

The dashboard executes the following PostgreSQL queries:

### Job Statistics
```sql
-- Jobs by source
SELECT source, COUNT(*) as count
FROM jobs
GROUP BY source
ORDER BY count DESC

-- Jobs by date (last 30 days)
SELECT DATE(discovered_date) as date, COUNT(*) as count
FROM jobs
WHERE discovered_date >= NOW() - INTERVAL '30 days'
GROUP BY DATE(discovered_date)
ORDER BY date DESC

-- Total jobs
SELECT COUNT(*) FROM jobs

-- Jobs today
SELECT COUNT(*) FROM jobs 
WHERE DATE(discovered_date) = CURRENT_DATE
```

### User Activity
```sql
-- Total users
SELECT COUNT(*) FROM users

-- Total CVs
SELECT COUNT(*) FROM cvs

-- Total matches
SELECT COUNT(*) FROM user_job_matches

-- Matches today
SELECT COUNT(*) FROM user_job_matches 
WHERE DATE(matched_date) = CURRENT_DATE

-- Match quality distribution
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
```

### Claude Analytics
```sql
-- Total Claude analyses
SELECT COUNT(*) FROM user_job_matches 
WHERE claude_score IS NOT NULL

-- Claude analyses today
SELECT COUNT(*) FROM user_job_matches 
WHERE claude_score IS NOT NULL 
AND DATE(matched_date) = CURRENT_DATE
```

### Top Lists
```sql
-- Top companies
SELECT company, COUNT(*) as count
FROM jobs
GROUP BY company
ORDER BY count DESC
LIMIT 10

-- Top locations
SELECT location, COUNT(*) as count
FROM jobs
WHERE location IS NOT NULL AND location != ''
GROUP BY location
ORDER BY count DESC
LIMIT 10
```

## API Quota Checking

The dashboard attempts to fetch quota information from RapidAPI for JSearch and Active Jobs:

### JSearch Quota Endpoint
```python
response = requests.get(
    'https://jsearch.p.rapidapi.com/quota',
    headers={
        'X-RapidAPI-Key': JSEARCH_API_KEY,
        'X-RapidAPI-Host': 'jsearch.p.rapidapi.com'
    },
    timeout=5
)
```

### Active Jobs Quota Endpoint
```python
response = requests.get(
    'https://active-jobs-db.p.rapidapi.com/quota',
    headers={
        'X-RapidAPI-Key': ACTIVEJOBS_API_KEY,
        'X-RapidAPI-Host': 'active-jobs-db.p.rapidapi.com'
    },
    timeout=5
)
```

**Note**: If these endpoints are not available or return errors, the dashboard shows "Unable to fetch - Check RapidAPI dashboard for details"

**Alternative**: Users can manually check quotas at https://rapidapi.com/dashboard

## Auto-Refresh

The dashboard automatically refreshes data every **2 minutes** (120,000 milliseconds) to provide near real-time monitoring.

**Manual Refresh**: Click the "🔄 Refresh Data" button in the dashboard header

## Visualizations

All charts use **Chart.js v4.4.0** from CDN:
- Responsive design (adapts to screen size)
- Interactive tooltips
- Legend controls
- Smooth animations

**Chart Colors**:
- Primary: `#667eea` (purple-blue)
- Secondary: `#764ba2` (purple)
- Accent colors: `#f093fb`, `#4facfe`, `#43e97b`, `#fa709a`, `#fee140`, `#30cfd0`

## Performance Considerations

### Database Query Optimization

Current queries are straightforward aggregations. For better performance with large datasets, consider adding indexes:

```sql
-- Recommended indexes
CREATE INDEX idx_jobs_discovered_date ON jobs(discovered_date DESC);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_ujm_created ON user_job_matches(matched_date DESC);
CREATE INDEX idx_ujm_semantic_score ON user_job_matches(semantic_score);
CREATE INDEX idx_jobs_company ON jobs(company);
CREATE INDEX idx_jobs_location ON jobs(location);
```

**Expected improvement**: Reduce stats query time from ~11.8s to 2-3s

### API Quota Calls

- Each RapidAPI quota check has a 5-second timeout
- Failed quota checks are caught and handled gracefully
- Does not block dashboard rendering

### Caching Considerations

For high-traffic deployments, consider caching `/api/stats` response:
- Cache TTL: 60 seconds
- Use Redis or Flask-Caching
- Invalidate on job creation/matching

## Error Handling

All database queries and API calls are wrapped in try/except blocks:

```python
try:
    # Execute query
    result = job_db.execute_query(sql)
    stats['metric'] = process(result)
except Exception as e:
    print(f"Error fetching metric: {e}")
    stats['metric'] = default_value
```

**Benefits**:
- Dashboard always loads (even if some data is unavailable)
- Errors logged to console for debugging
- Graceful degradation (shows 0 or "N/A" for failed metrics)

## Security

### Authentication
- All routes require login (`@login_required`)
- Uses Flask-Login session management
- No public access to statistics

### API Keys
- JSearch and Active Jobs keys stored in environment variables
- Never exposed in API responses
- Used only for quota checking

### Data Privacy
- No personally identifiable information (PII) exposed
- Aggregated statistics only
- Company/location data is public job posting information

## Troubleshooting

### "Unable to fetch" API Quota

**Possible causes**:
1. API key not configured in environment variables
2. RapidAPI service down or changed endpoints
3. Network connectivity issues
4. Rate limiting on quota endpoint

**Solutions**:
1. Check `.env` file for `JSEARCH_API_KEY` and `ACTIVEJOBS_API_KEY`
2. Verify keys at https://rapidapi.com/dashboard
3. Check RapidAPI service status
4. Manually check quotas on RapidAPI dashboard

### Charts Not Rendering

**Possible causes**:
1. Chart.js CDN not loading
2. JavaScript errors in console
3. No data available for chart

**Solutions**:
1. Check browser console for errors
2. Verify internet connection (for CDN)
3. Ensure database has data (`total_jobs > 0`)

### Slow Dashboard Loading

**Possible causes**:
1. Large dataset (millions of jobs)
2. No database indexes
3. Network latency to PostgreSQL (Railway)

**Solutions**:
1. Add recommended indexes (see Performance Considerations)
2. Consider query result caching
3. Use connection pooling for PostgreSQL

## Future Enhancements

Potential improvements for the dashboard:

### 1. User-Specific Statistics
- Matches per user
- Top matched companies per user
- User engagement metrics

### 2. Performance Monitoring
- Average matching time per job
- Database query performance
- API response times

### 3. Alert System
- Email notifications when API quota < 20%
- Slack/Discord webhook for errors
- Daily summary reports

### 4. Export Capabilities
- Download stats as CSV/Excel
- PDF report generation
- Scheduled email reports

### 5. Historical Trends
- 90-day job collection trends
- Month-over-month growth
- Seasonal hiring patterns

### 6. Advanced Filters
- Date range selector
- Source-specific drill-down
- User segment analysis

### 7. Real-Time Updates
- WebSocket integration for live data
- Server-Sent Events (SSE) for notifications
- Live user count

### 8. Cost Tracking
- Detailed API cost breakdown
- Claude API usage cost
- Database hosting costs

## Files Modified

1. **app.py** (Lines ~1594-1800):
   - Added `/admin/stats` route (HTML dashboard)
   - Added `/api/stats` route (JSON endpoint)
   - Implemented all statistics gathering logic
   - API quota checking for JSearch and Active Jobs

2. **web/templates/admin_stats.html** (NEW):
   - Complete dashboard HTML template
   - Chart.js integration
   - Responsive grid layouts
   - Auto-refresh functionality

3. **web/templates/base.html** (Line 253):
   - Added "📊 Stats" link to navigation
   - Highlighted with gold background

## Usage Examples

### Accessing the Dashboard
1. Login to Job Monitor
2. Click "📊 Stats" in the top navigation
3. View all metrics and charts
4. Click "🔄 Refresh Data" to update

### Programmatic Access
```python
import requests

# Authenticate and get session cookie
session = requests.Session()
session.post('http://localhost:8080/login', data={
    'email': 'user@example.com',
    'password': 'password'
})

# Fetch stats
response = session.get('http://localhost:8080/api/stats')
stats = response.json()

# Access specific metrics
print(f"Total jobs: {stats['total_jobs']}")
print(f"JSearch quota: {stats['api_quotas']['jsearch']['requests_remaining']}")
```

### Monitoring API Quotas
```python
# Check if we're running low on JSearch requests
jsearch_remaining = stats['api_quotas']['jsearch']['requests_remaining']
jsearch_limit = stats['api_quotas']['jsearch']['requests_limit']

if isinstance(jsearch_remaining, int) and isinstance(jsearch_limit, int):
    percentage = (jsearch_remaining / jsearch_limit) * 100
    if percentage < 20:
        print(f"⚠️ JSearch quota low: {percentage:.1f}% remaining")
```

## Maintenance

### Regular Checks
- Weekly: Review API quota usage trends
- Monthly: Analyze job collection performance
- Quarterly: Evaluate cost vs. value of paid APIs

### Database Maintenance
- Monthly: Run `VACUUM ANALYZE` on PostgreSQL
- Quarterly: Review and optimize slow queries
- Annually: Evaluate data retention policies

### Monitoring Alerts
Set up monitoring for:
- API quota < 20% remaining
- Database response time > 5 seconds
- Failed job collections > 10% per day
- No jobs collected in 24 hours

## Support

For issues or questions:
1. Check browser console for JavaScript errors
2. Check Flask logs for backend errors
3. Verify database connectivity
4. Check RapidAPI dashboard for service status

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Author**: Job Monitor Development Team
