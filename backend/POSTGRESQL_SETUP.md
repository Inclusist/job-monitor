# PostgreSQL Migration Guide

## Overview

The job-monitor application now supports both SQLite (for local development) and PostgreSQL (for production deployment). The system automatically detects which database to use based on environment variables.

## Architecture

- **Local Development**: SQLite (`data/jobs.db`)
- **Production**: PostgreSQL (Railway or other hosting)
- **Auto-Detection**: `DATABASE_URL` environment variable determines database type

## Setup Instructions

### 1. Install PostgreSQL Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `sqlalchemy==2.0.23` - Database abstraction (for future use)

### 2. Provision PostgreSQL on Railway

1. Open Railway dashboard: https://railway.app
2. Select your job-monitor project
3. Click **"New"** → **"Database"** → **"Add PostgreSQL"**
4. Railway will automatically create a PostgreSQL instance
5. Copy the `DATABASE_URL` connection string

The format will be:
```
postgresql://postgres:PASSWORD@HOST:PORT/railway
```

### 3. Configure Environment Variable

#### On Railway:
1. Go to your job-monitor service settings
2. Click **"Variables"** tab
3. Click **"New Variable"**
4. Name: `DATABASE_URL`
5. Value: Paste the PostgreSQL connection string from step 2
6. Click **"Add"**
7. Redeploy the service

#### Locally (for testing):
```bash
# Add to .env file
echo "DATABASE_URL=postgresql://..." >> .env

# Or export for current session
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

### 4. Migrate Existing Data

Run the migration script to transfer your SQLite data to PostgreSQL:

```bash
# With Railway DATABASE_URL
python scripts/migrate_to_postgres.py "postgresql://postgres:PASSWORD@HOST:PORT/railway"

# Or if DATABASE_URL is in environment
python scripts/migrate_to_postgres.py "$DATABASE_URL"
```

The script will:
- ✓ Migrate all jobs (with deduplication)
- ✓ Migrate user job matches
- ✓ Preserve data integrity
- ✓ Skip duplicates (based on job_id)
- ✓ Provide detailed progress logging

**Migration Statistics Example:**
```
Jobs:
  ✓ Migrated: 2085
  ⊘ Skipped:  0
  ✗ Errors:   0

User Job Matches:
  ✓ Migrated: 857
  ⊘ Skipped:  0
  ✗ Errors:   0
```

### 5. Verify Migration

#### Check Database Connection:
```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://..."

# Start app (will auto-connect to PostgreSQL)
python app.py
```

#### Check Logs:
Look for:
```
INFO:src.database.factory:Using PostgreSQL database
INFO:src.database.postgres_operations:PostgreSQL connection pool created successfully
```

#### Check Data:
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
```

## Database Features

### PostgreSQL Advantages:
- ✓ **Connection Pooling**: 1-10 connections for concurrent access
- ✓ **Better Concurrency**: Multiple users can access simultaneously
- ✓ **Automatic Backups**: Railway backs up daily
- ✓ **Proper Types**: SERIAL for auto-increment, TIMESTAMP for dates
- ✓ **UPSERT Support**: ON CONFLICT DO UPDATE for user matches
- ✓ **Indexes**: Optimized for user_id, job_id, score queries
- ✓ **Foreign Keys**: Proper CASCADE deletes

### SQLite (Local Dev):
- ✓ **No Setup**: Works out of the box
- ✓ **Fast**: Great for development
- ✓ **File-Based**: Easy to backup/reset
- ✓ **Portable**: Single file database

## Database Schema

### Tables (8 total):

1. **jobs**: Job listings with match analysis
2. **search_history**: User search tracking
3. **applications**: Job application tracking
4. **job_feedback**: User feedback for ML
5. **user_job_matches**: Per-user semantic matches
6. **users**: User authentication
7. **cvs**: CV file metadata
8. **cv_profiles**: Parsed CV data

### Key Indexes:
- `idx_user_job_matches_user_id` - Fast user queries
- `idx_user_job_matches_job_id` - Fast job queries
- `idx_user_job_matches_scores` - Fast score filtering

## Troubleshooting

### Issue: "relation 'jobs' does not exist"
**Solution**: Tables are created automatically on first connection. Restart the app.

### Issue: "connection refused"
**Solution**: 
1. Verify DATABASE_URL is correct
2. Check Railway PostgreSQL is running
3. Ensure IP is whitelisted (Railway allows all by default)

### Issue: "too many connections"
**Solution**: Connection pool is limited to 10. Check for unclosed connections or increase pool size in `postgres_operations.py`:
```python
self.pool = SimpleConnectionPool(1, 20, dsn=db_url)  # Increase from 10 to 20
```

### Issue: "duplicate key value"
**Solution**: Jobs are deduplicated by `job_id`. This is expected behavior. The job will be skipped.

### Issue: Migration script hangs
**Solution**: 
1. Check PostgreSQL is accessible
2. Verify DATABASE_URL format is correct
3. Check for large BLOB data (should be minimal)

## Rollback to SQLite

If you need to switch back to SQLite:

```bash
# Remove DATABASE_URL environment variable
unset DATABASE_URL

# Restart app - will auto-detect and use SQLite
python app.py
```

On Railway:
1. Go to Variables tab
2. Delete `DATABASE_URL` variable
3. Redeploy

## Performance Considerations

### PostgreSQL:
- **Query Time**: ~10-50ms for typical queries
- **Insert Time**: ~2-5ms per job
- **Connection Time**: ~50-100ms (pooled connections reused)
- **Recommended**: Use for production with multiple users

### SQLite:
- **Query Time**: ~5-20ms for typical queries
- **Insert Time**: ~1-2ms per job
- **Connection Time**: Instant (file-based)
- **Recommended**: Use for local development and single-user setups

## Cost Analysis

### Railway Pricing:

**SQLite on Volume**:
- ❌ Volume storage: $0.25/GB/month
- ❌ 10MB database = ~$2.50/month (minimum volume charge)
- ❌ No backups
- ❌ File I/O limitations

**PostgreSQL Database**:
- ✓ Free tier: 512MB storage, 1GB RAM
- ✓ Automatic daily backups
- ✓ Better performance with concurrent users
- ✓ Upgrade to Hobby plan: $5/month for 2GB storage

**Recommendation**: Use PostgreSQL on Railway for cost savings and better features.

## Monitoring

### Check Connection Pool Status:
```sql
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE datname = current_database();
```

### Check Database Size:
```sql
SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;
```

### Check Table Sizes:
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Support

For issues or questions:
1. Check Railway logs for connection errors
2. Verify DATABASE_URL format
3. Test connection with `psql $DATABASE_URL`
4. Check migration script output for detailed error messages

---

**Status**: ✅ PostgreSQL support fully implemented and tested
**Version**: 1.0
**Last Updated**: December 2025
