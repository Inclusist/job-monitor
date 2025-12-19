# Railway Deployment Troubleshooting & PostgreSQL Migration Plan

## Current Repo Status ✅
- **Git repo size**: 428 KB (very small, not the issue)
- **Large files excluded**: venv/, data/, *.db properly ignored
- **Docker config**: Looks correct

## Railway Build Failure - Common Causes

### 1. **Build Timeout** (Most Likely)
Railway free tier has a 10-minute build timeout. Your build includes:
- Installing system packages (gcc, g++, poppler)
- Installing Python packages including **sentence-transformers** (~500MB download)
- Downloading the AI model on first run

**Solution**: Pre-download model in Docker build

### 2. **Memory Limits**
Railway Hobby plan: 512MB-1GB RAM
Your app needs:
- Sentence transformer model: ~500MB RAM when loaded
- Flask app: ~100-200MB
- Total: ~600-700MB (tight but possible)

**Solution**: Use smaller model or upgrade to Pro plan ($5/month = 2GB RAM)

### 3. **Port Configuration**
Railway assigns a random PORT via environment variable.

**Current code** (app.py lines 1505-1512):
```python
port = int(os.environ.get('PORT', 8080))
debug = os.environ.get('FLASK_ENV') != 'production'
app.run(debug=debug, host='0.0.0.0', port=port)
```
✅ This looks correct

---

## Quick Fixes to Try

### Fix 1: Optimize Dockerfile (Pre-download Model)

Create this improved Dockerfile:

```dockerfile
# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model during build
# This prevents timeout on first run
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data temp_uploads data/logs

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
```

### Fix 2: Use Smaller Model (If Memory is Issue)

Replace `all-MiniLM-L6-v2` with `all-MiniLM-L3-v2`:
- L6-v2: 384 dimensions, ~500MB
- L3-v2: 384 dimensions, ~120MB (4x smaller!)
- Performance: 2-3% accuracy drop, but 4x faster and lighter

### Fix 3: Add Railway Health Check Delay

Update railway.toml:
```toml
[deploy]
healthcheckTimeout = 600  # Increase to 10 minutes
```

---

## PostgreSQL Migration Plan

### Why Migrate?
1. **Scalability**: SQLite locks entire database on write
2. **Concurrent Users**: PostgreSQL handles multiple users better
3. **Railway Integration**: Free PostgreSQL database included with Hobby plan
4. **Data Safety**: Better backup/restore, no file corruption issues
5. **Advanced Features**: Full-text search, JSON queries, better indexing

### Cost Analysis
- **SQLite on Railway**: 
  - Need persistent volume ($5/month for 1GB)
  - Risk of data loss if volume not configured
  - Limited to single-server deployment

- **PostgreSQL on Railway**:
  - FREE with Hobby plan (500MB storage)
  - Automatic backups
  - Can scale to multiple app instances
  - Better for production

### Migration Steps

#### Phase 1: Create PostgreSQL Database (5 minutes)
1. In Railway dashboard, click "New" → "Database" → "Add PostgreSQL"
2. Railway provisions database and provides connection URL
3. Copy `DATABASE_URL` environment variable

#### Phase 2: Update Code (30 minutes)
1. Add PostgreSQL dependencies:
   ```bash
   pip install psycopg2-binary sqlalchemy
   ```

2. Update `requirements.txt`:
   ```
   psycopg2-binary==2.9.9
   sqlalchemy==2.0.23
   ```

3. Create new database operations file:
   `src/database/postgres_operations.py`

4. Update app.py to use PostgreSQL when `DATABASE_URL` exists

#### Phase 3: Migrate Data (10 minutes)
1. Export from SQLite:
   ```bash
   sqlite3 data/jobs.db .dump > backup.sql
   ```

2. Convert and import to PostgreSQL (script provided)

#### Phase 4: Test and Deploy (15 minutes)
1. Test locally with PostgreSQL
2. Push to Railway
3. Verify data migration
4. Update environment variables

### Backward Compatibility
The code can support BOTH:
```python
# Auto-detect database type
DATABASE_URL = os.environ.get('DATABASE_URL')  # PostgreSQL
if DATABASE_URL:
    db = PostgresDatabase(DATABASE_URL)
else:
    db = SQLiteDatabase('data/jobs.db')  # Local development
```

---

## Recommended Immediate Actions

### Option A: Quick Fix for Railway (Try First)
1. ✅ Update Dockerfile to pre-download model
2. ✅ Push to main branch
3. ✅ Redeploy on Railway
4. ✅ Watch build logs for errors
5. ⏳ Wait 5-10 minutes for first build

**Estimated time**: 15 minutes

### Option B: Migrate to PostgreSQL (Better Long-term)
1. ✅ Create PostgreSQL database on Railway
2. ✅ Update code for PostgreSQL support
3. ✅ Migrate data
4. ✅ Deploy with PostgreSQL
5. ✅ Remove SQLite volume requirement

**Estimated time**: 1 hour

### My Recommendation: **Do Both!**

**Now** (15 minutes):
- Fix Dockerfile to pre-download model
- Try deploying again
- This should work for initial launch

**This Week** (1 hour):
- Migrate to PostgreSQL
- Better scalability
- No volume costs
- Production-ready setup

---

## Next Steps

**What would you like to do?**

1. **Fix Railway deployment now** - I'll update the Dockerfile and help you redeploy
2. **Migrate to PostgreSQL now** - I'll create the migration code and guide you through Railway setup
3. **Do both** - Fix deployment first, then plan PostgreSQL migration
4. **See Railway error logs** - Help me diagnose the actual error from Railway

Let me know which approach you prefer!
