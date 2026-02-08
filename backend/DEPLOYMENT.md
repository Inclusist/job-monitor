# Railway Deployment Guide

## Prerequisites
1. Railway account (sign up at https://railway.app with GitHub)
2. GitHub repository with your code pushed

## Step-by-Step Deployment

### 1. Push Code to GitHub
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 2. Create Railway Project
1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `job-monitor` repository
5. Railway will auto-detect the Dockerfile

### 3. Add Persistent Volume (IMPORTANT!)
1. In your Railway project, click on your service
2. Go to "Variables" tab
3. Click "Add Volume"
4. Mount path: `/app/data`
5. This ensures your SQLite database persists across deployments

### 4. Configure Environment Variables
In Railway dashboard → Variables, add these:

**Required:**
- `ANTHROPIC_API_KEY` - Your Claude API key
- `DATABASE_PATH` - Set to `data/jobs.db`

**Optional (Job Collectors):**
- `JSEARCH_API_KEY`
- `ACTIVEJOBS_API_KEY`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`

**Email (if needed):**
- `SMTP_SERVER`
- `SMTP_PORT`
- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`
- `RECIPIENT_EMAIL`

### 5. Deploy
Railway will automatically deploy when you push to main branch.

First deployment takes ~5-10 minutes (downloads AI models).

### 6. Get Your URL
1. In Railway project, click "Settings"
2. Under "Networking" → Generate Domain
3. Your app will be live at: `https://your-app-name.up.railway.app`

## Post-Deployment

### Monitor Logs
```bash
# Install Railway CLI (optional)
npm i -g @railway/cli
railway login
railway logs
```

### Database Backup
Railway volumes are persistent, but create backups:
```bash
railway run sqlite3 data/jobs.db ".backup backup.db"
```

## Troubleshooting

### Out of Memory
- Upgrade to Hobby plan ($5/mo with 512MB-8GB RAM)
- The sentence-transformers model needs ~500MB

### Cold Starts
- Free tier sleeps after 30 min inactivity
- Upgrade to prevent sleep

### Database Locked
- SQLite doesn't handle many concurrent users well
- Consider migrating to PostgreSQL for >10 concurrent users

## Scaling Considerations

For production with many users:
1. Migrate SQLite → PostgreSQL (Railway provides free PostgreSQL)
2. Add Redis for background job queue
3. Use Celery for async job matching
4. Store CVs in S3/Cloudflare R2

## Cost Estimate
- **Free tier:** $5 credit/month (enough for testing with 1-2 users)
- **Hobby:** $5/month (persistent, no sleep, good for small team)
- **Pro:** $20/month (better resources, multiple services)

Your app with current usage: ~$5-10/month on Hobby plan.
