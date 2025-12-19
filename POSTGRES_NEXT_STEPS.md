# PostgreSQL Migration - Next Steps

## ✅ Completed

1. **PostgreSQL Dependencies**
   - ✓ Added `psycopg2-binary>=2.9.9` to requirements.txt
   - ✓ Added `sqlalchemy>=2.0.23` to requirements.txt
   - ✓ Installed locally (version 2.9.11 with Python 3.13 support)

2. **PostgreSQL Database Class**
   - ✓ Created `src/database/postgres_operations.py` (475 lines)
   - ✓ Connection pooling: 1-10 concurrent connections
   - ✓ Compatible interface with SQLite version
   - ✓ Proper SQL types: SERIAL, TIMESTAMP, TEXT[]
   - ✓ UPSERT support for user_job_matches
   - ✓ Indexes for performance

3. **Database Factory Pattern**
   - ✓ Created `src/database/factory.py` (34 lines)
   - ✓ Auto-detects DATABASE_URL environment variable
   - ✓ Returns PostgresDatabase if postgres:// URL found
   - ✓ Falls back to JobDatabase (SQLite) otherwise
   - ✓ **Tested and working!**

4. **Updated All Application Files**
   - ✓ `app.py` - Main Flask application
   - ✓ `main.py` - Daily monitoring script
   - ✓ `scripts/filter_jobs.py` - Semantic filtering
   - ✓ `scripts/analyze_jobs.py` - Claude analysis
   - ✓ `scripts/bulk_fetch_jobs.py` - Bulk job collection
   - ✓ `scripts/fetch_arbeitsagentur_jobs.py` - German jobs
   - ✓ `scripts/analyze_sources.py` - Source quality analysis

5. **Migration Script**
   - ✓ Created `scripts/migrate_to_postgres.py` (248 lines)
   - ✓ Migrates jobs table with deduplication
   - ✓ Migrates user_job_matches with proper upserts
   - ✓ Detailed progress logging
   - ✓ Confirmation prompt for safety

6. **Documentation**
   - ✓ Created `POSTGRESQL_SETUP.md` - Complete setup guide
   - ✓ Covers Railway provisioning, local testing, troubleshooting
   - ✓ Performance considerations and cost analysis

## 📋 Next Steps for You

### Step 1: Monitor Railway Deployment (In Progress)

Check Railway dashboard for the latest deployment from commit `f1b4078`:
- Look for: "Downloading model..." message during build
- Should complete in ~8 minutes
- If successful, app will be online with pre-downloaded AI model

### Step 2: Provision PostgreSQL on Railway

1. Open Railway dashboard: https://railway.app
2. Select your **job-monitor** project
3. Click **"New"** → **"Database"** → **"Add PostgreSQL"**
4. Railway creates PostgreSQL instance automatically (free 512MB plan)
5. Click on the PostgreSQL service
6. Go to **"Connect"** tab
7. Copy the **`DATABASE_URL`** value (starts with `postgresql://`)

### Step 3: Add DATABASE_URL to Railway

1. Go back to your **job-monitor** service (not the PostgreSQL service)
2. Click **"Variables"** tab
3. Click **"New Variable"**
4. Name: `DATABASE_URL`
5. Value: Paste the connection string from Step 2
6. Click **"Add"**
7. Railway will automatically redeploy the service

**Expected behavior after redeploy:**
- App will auto-detect PostgreSQL from DATABASE_URL
- Logs will show: `Using PostgreSQL database`
- Tables will be created automatically on first connection

### Step 4: Migrate Data from SQLite to PostgreSQL

Once Railway is running with PostgreSQL:

```bash
# Get the DATABASE_URL from Railway dashboard
# Copy it from the PostgreSQL service → Connect tab

# Run migration script
python scripts/migrate_to_postgres.py "postgresql://postgres:PASSWORD@HOST:PORT/railway"

# Or if you've added it to your .env file:
python scripts/migrate_to_postgres.py "$DATABASE_URL"
```

**What the migration does:**
- Reads all 2085 jobs from SQLite (data/jobs.db)
- Uploads to PostgreSQL with deduplication
- Migrates user_job_matches (857 matches for user 3)
- Provides detailed progress logging
- Skips duplicates (based on job_id)

**Expected output:**
```
Starting jobs migration...
Found 2085 jobs to migrate
Migrated 100 jobs...
Migrated 200 jobs...
...
Jobs migration complete: 2085 migrated, 0 skipped, 0 errors

Starting user_job_matches migration...
Found 857 user job matches to migrate
Migrated 100 matches...
...
Matches migration complete: 857 migrated, 0 skipped, 0 errors

✓ Migration completed successfully!
```

### Step 5: Verify PostgreSQL Integration

**Check Railway Logs:**
```
INFO:src.database.factory:Using PostgreSQL database
INFO:src.database.postgres_operations:PostgreSQL connection pool created successfully
INFO:src.database.postgres_operations:PostgreSQL tables created successfully
```

**Test Locally (Optional):**
```bash
# Copy DATABASE_URL from Railway
export DATABASE_URL="postgresql://..."

# Start app - should connect to Railway PostgreSQL
source venv/bin/activate
python app.py

# Should see:
# INFO:src.database.factory:Using PostgreSQL database
# INFO:src.database.postgres_operations:PostgreSQL connection pool created successfully
```

**Verify Data:**
```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Or use psql directly
psql "$DATABASE_URL"

# Check tables
\dt

# Check row counts
SELECT 'jobs' as table_name, COUNT(*) FROM jobs
UNION ALL
SELECT 'user_job_matches', COUNT(*) FROM user_job_matches;

# Should show:
#   jobs: 2085
#   user_job_matches: 857
```

### Step 6: Rollback Plan (If Needed)

If something goes wrong, you can instantly rollback:

**On Railway:**
1. Go to Variables tab
2. Delete `DATABASE_URL` variable
3. Redeploy
4. App will fall back to SQLite

**Locally:**
```bash
unset DATABASE_URL
python app.py  # Uses SQLite
```

Your SQLite data is never modified, so you can always go back.

## 🔍 Troubleshooting

### "relation 'jobs' does not exist"
- **Cause**: Tables not created yet
- **Fix**: Restart the app - tables are created automatically on first connection

### "connection refused"
- **Cause**: Wrong DATABASE_URL or PostgreSQL not running
- **Fix**: Verify DATABASE_URL from Railway dashboard, ensure PostgreSQL service is running

### "too many connections"
- **Cause**: Connection pool exhausted (>10 concurrent)
- **Fix**: Increase pool size in `src/database/postgres_operations.py`:
  ```python
  self.pool = SimpleConnectionPool(1, 20, dsn=db_url)  # Increase from 10 to 20
  ```

### Migration script hangs
- **Cause**: Network issue or large data
- **Fix**: Check PostgreSQL is accessible, verify DATABASE_URL format

## 📊 Current Database Status

- **SQLite (Local)**: 10MB, 2085 jobs, 857 matches, 8 tables
- **PostgreSQL (Ready)**: Will have same data after migration
- **Connection**: Auto-detection via DATABASE_URL environment variable
- **Backward Compatible**: Remove DATABASE_URL to use SQLite

## 🎯 Why PostgreSQL?

1. **Cost**: Free 512MB on Railway (vs $2.50+/month for SQLite volume)
2. **Performance**: Better concurrent access for multiple users
3. **Features**: Connection pooling, automatic backups, UPSERT support
4. **Scalability**: Handles growth better than file-based SQLite
5. **Production-Ready**: Industry standard for web applications

## 📝 Additional Notes

- **Development**: Continue using SQLite locally (faster, simpler)
- **Production**: Use PostgreSQL on Railway (better for multiple users)
- **Testing**: Can test PostgreSQL locally with Railway connection string
- **Deployment**: Railway auto-deploys on git push to main branch
- **Monitoring**: Check Railway logs for connection pool usage

---

**Ready to proceed!** Follow the steps above to complete the PostgreSQL migration.
