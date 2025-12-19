# Railway Deployment Debugging Guide

## Common Deployment Failures

### 1. Build Timeout (Most Likely)

**Symptoms:**
- Build stops after ~10 minutes
- Error: "Build exceeded maximum time limit"

**Causes:**
- Downloading 500MB sentence-transformers model
- Building psycopg2-binary from source
- Installing all dependencies

**Solutions:**

**Option A: Upgrade to Hobby Plan ($5/month)**
- Longer build timeout (20 minutes vs 10 minutes)
- More memory during build
- Most reliable solution

**Option B: Optimize Build (Current Fix)**
- ✅ Pre-download model in Dockerfile (done)
- ✅ Add libpq-dev for psycopg2 (done)
- ✅ Use --no-cache-dir for pip (done)

**Option C: Use Smaller Model**
```dockerfile
# Replace in Dockerfile:
RUN python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('sentence-transformers/all-MiniLM-L3-v2')"
```
- L3-v2: 61MB (vs L6-v2: 500MB)
- Slightly lower quality but much faster

### 2. Memory Exceeded

**Symptoms:**
- Build completes but app crashes on startup
- Error: "Out of memory" or "Killed"

**Causes:**
- Free tier: 512MB RAM
- Sentence-transformers model: ~400-500MB RAM
- Flask app: ~50-100MB RAM
- **Total: 450-600MB (exceeds free tier)**

**Solutions:**

**Immediate Fix:** Reduce memory usage
```python
# In app.py or main.py, add:
import torch
torch.set_num_threads(1)  # Reduce CPU threads

# When loading model:
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
model.half()  # Use half-precision (reduces RAM by 50%)
```

**Long-term Fix:** Upgrade to Hobby Plan
- 2GB RAM vs 512MB
- Plenty of headroom for model + app

### 3. Port Binding Issues

**Symptoms:**
- Build succeeds, healthcheck fails
- Error: "Failed to bind to port"

**Current Config:**
```python
# app.py uses PORT env var (correct for Railway)
port = int(os.environ.get('PORT', 8080))
app.run(host='0.0.0.0', port=port)
```

**Verify:**
- Railway automatically sets PORT env var
- Healthcheck path: `/` (should return 200)
- Timeout: 600 seconds (increased from 300)

### 4. PostgreSQL Build Failure

**Symptoms:**
- Error during pip install psycopg2-binary
- "pg_config not found" or "libpq-fe.h not found"

**Fix Applied:**
```dockerfile
# Added to Dockerfile:
libpq-dev \
```

**Verify:** Check build logs for:
```
Successfully installed psycopg2-binary-2.9.11
```

## Debugging Steps

### Step 1: Check Build Logs

In Railway dashboard:
1. Click on your job-monitor service
2. Go to "Deployments" tab
3. Click on the latest deployment
4. Check "Build Logs"

**Look for:**
- ✅ "Downloading model..." (confirms model pre-download)
- ✅ "Model ready!" (confirms model loaded)
- ✅ "Successfully installed psycopg2-binary"
- ❌ "timeout" or "exceeded"
- ❌ "out of memory" or "killed"

### Step 2: Check Runtime Logs

After build completes:
1. Go to "Logs" tab
2. Look for startup messages

**Good logs:**
```
INFO:src.database.factory:Using SQLite database
INFO:werkzeug: * Running on all addresses (0.0.0.0)
INFO:werkzeug: * Running on http://0.0.0.0:8080
```

**Bad logs:**
```
Killed
MemoryError
ImportError: No module named 'psycopg2'
```

### Step 3: Check Healthcheck

Railway pings `/` endpoint every few seconds:
- Should return 200 status
- Timeout: 600 seconds (10 minutes)

**If healthcheck fails:**
- Check if Flask is binding to correct port
- Check if model loading is hanging
- Check logs for errors

## Quick Fixes by Error Type

### "Build timeout exceeded"
```bash
# Option 1: Upgrade to Hobby plan
# Option 2: Use smaller model (see Option C above)
# Option 3: Comment out model pre-download, load on first request
```

### "Out of memory"
```python
# Add to app.py after imports:
import torch
torch.set_num_threads(1)

# When loading model (in filter_jobs.py, analyze_jobs.py):
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
model.half()  # Reduces memory by 50%
```

### "psycopg2 build failed"
```dockerfile
# Verify libpq-dev is in Dockerfile:
RUN apt-get update && apt-get install -y \
    libpq-dev \
```

### "Healthcheck failed"
```python
# Verify app.py has:
port = int(os.environ.get('PORT', 8080))
app.run(host='0.0.0.0', port=port, debug=False)
```

## Current Deployment Status

**Latest Changes (Commit: db67514):**
- ✅ Added libpq-dev for PostgreSQL
- ✅ Pre-download model in Dockerfile
- ✅ Healthcheck timeout: 600s
- ✅ PostgreSQL support added (optional)

**Expected Build Time:**
- Free tier: 8-12 minutes
- Hobby tier: 5-8 minutes

**Expected Memory Usage:**
- Without model: ~100MB
- With model loaded: ~550MB ⚠️ (exceeds free tier)

## Recommendations

### For Free Tier (512MB RAM):

**Don't load model at startup** - Load only when needed:
```python
# Remove global model loading
# Instead, load in functions when called:
def filter_jobs():
    model = SentenceTransformer('...')  # Loads on demand
    # ... use model ...
    del model  # Free memory after use
```

### For Hobby Tier ($5/month):

**Pre-load model** - Keep current approach:
- Faster response times
- Model stays in memory
- No cold start delays

## Testing Locally

Test Railway-like environment locally:

```bash
# Build Docker image
docker build -t job-monitor .

# Run with Railway-like config
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e FLASK_ENV=production \
  -e DATABASE_PATH=/app/data/jobs.db \
  job-monitor

# Test healthcheck
curl http://localhost:8080/
```

## Next Steps

1. **Check Railway logs** - See exact error message
2. **Try smaller model** - If build timeout
3. **Upgrade plan** - If memory exceeded
4. **Remove model pre-load** - If staying on free tier

---

**Need Help?**
Share the Railway deployment logs and I can provide specific fixes!
