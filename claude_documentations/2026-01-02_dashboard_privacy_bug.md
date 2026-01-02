# Critical Privacy Bug: Dashboard Shows All Users' Shortlisted Jobs

**Date:** January 2, 2026
**Severity:** 🚨 CRITICAL - Privacy/Security Issue
**Status:** 🔴 Unresolved - Requires Immediate Fix

---

## Problem Summary

The dashboard shows shortlisted jobs from **ALL users**, not just the current user. When User A shortcuts a job, Users B, C, and D also see it in their dashboard.

---

## Root Cause Analysis

### Issue #1: `get_shortlisted_jobs()` Ignores User Parameter

**File:** `src/database/postgres_operations.py` (lines 1016-1030)

```python
def get_shortlisted_jobs(self, user_email: str = 'default@localhost') -> List[Dict]:
    """Get jobs marked as shortlisted by user"""
    conn = self._get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM jobs
            WHERE status = 'shortlisted'  # ❌ NO USER FILTERING!
            ORDER BY match_score DESC, discovered_date DESC
        """)
        results = [dict(row) for row in cursor.fetchall()]
        return results
```

**Problem:** Function accepts `user_email` parameter but **never uses it** in the query!

---

### Issue #2: Wrong Status Field Being Updated

**File:** `app.py` (lines 1420-1441)

```python
@app.route('/jobs/<int:job_id>/shortlist', methods=['POST'])
def shortlist_job(job_id):
    """Add job to shortlist"""
    try:
        job_db.update_job_status(job_id, 'shortlisted')  # ❌ Updates GLOBAL status!
        flash('Job added to your dashboard!', 'success')
    except Exception as e:
        flash(f'Error adding job to shortlist: {str(e)}', 'error')

    return redirect(request.referrer or url_for('jobs'))

@app.route('/jobs/<int:job_id>/remove-shortlist', methods=['POST'])
def remove_shortlist(job_id):
    """Remove job from shortlist"""
    try:
        job_db.update_job_status(job_id, 'viewed')  # ❌ Updates GLOBAL status!
        flash('Job removed from dashboard', 'info')
    except Exception as e:
        flash(f'Error removing job: {str(e)}', 'error')

    return redirect(request.referrer or url_for('dashboard'))
```

**Problem:** Updates `jobs.status` (global field affecting all users) instead of `user_job_matches.status` (user-specific).

---

## Database Architecture

### Current Architecture (Correct)

Two tables exist:

1. **`jobs` table** - Global job data (shared across all users)
   - `id`, `title`, `company`, `location`, `description`, etc.
   - `status` - Should be for system-level status only (e.g., 'deleted', 'active')

2. **`user_job_matches` table** - User-specific job interactions
   ```sql
   CREATE TABLE user_job_matches (
       id SERIAL PRIMARY KEY,
       user_id INTEGER NOT NULL,        -- Links to specific user
       job_id INTEGER NOT NULL,          -- Links to job
       semantic_score INTEGER,
       claude_score INTEGER,
       priority TEXT,
       match_reasoning TEXT,
       key_alignments TEXT,
       potential_gaps TEXT,
       status TEXT,                      -- USER-SPECIFIC status!
       created_date TIMESTAMP NOT NULL,
       last_updated TIMESTAMP NOT NULL
   );
   ```

**Correct Architecture:** User-specific actions (shortlist, delete, apply) should update `user_job_matches.status`, not `jobs.status`.

---

## Impact

### Data Exposed
- User A shortcuts "Senior ML Engineer at Google" → Shows in User B's dashboard
- User C deletes "Data Scientist at Amazon" → Disappears from User D's job list
- All user job actions are visible to all other users

### Privacy Violation
- ✅ Users can see what jobs others are interested in
- ✅ Job search preferences are exposed
- ✅ Application intent is leaked

### User Experience
- Users see random jobs they didn't shortlist
- Users' shortlisted jobs disappear when other users remove them
- Dashboard becomes unusable with multiple users

---

## Solution Design

### Fix #1: Update `get_shortlisted_jobs()` Method

**File:** `src/database/postgres_operations.py`

```python
def get_shortlisted_jobs(self, user_email: str = 'default@localhost') -> List[Dict]:
    """Get jobs marked as shortlisted by user"""
    conn = self._get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        user_row = cursor.fetchone()
        if not user_row:
            return []
        user_id = user_row['id']

        # Query jobs with user-specific status
        cursor.execute("""
            SELECT j.*, ujm.status as user_status, ujm.priority as user_priority,
                   ujm.claude_score, ujm.match_reasoning, ujm.key_alignments,
                   ujm.potential_gaps
            FROM jobs j
            INNER JOIN user_job_matches ujm ON j.id = ujm.job_id
            WHERE ujm.user_id = %s
            AND ujm.status = 'shortlisted'
            ORDER BY ujm.claude_score DESC NULLS LAST,
                     ujm.semantic_score DESC NULLS LAST,
                     j.discovered_date DESC
        """, (user_id,))

        results = [dict(row) for row in cursor.fetchall()]
        return results
    finally:
        cursor.close()
        self._return_connection(conn)
```

**Changes:**
1. Get `user_id` from `user_email`
2. JOIN with `user_job_matches` table
3. Filter by `ujm.user_id = %s` AND `ujm.status = 'shortlisted'`
4. Return user-specific match data (scores, reasoning, etc.)

---

### Fix #2: Create User-Specific Status Update Methods

**File:** `src/database/postgres_operations.py`

```python
def update_user_job_status(self, user_id: int, job_id: int, status: str, notes: str = None):
    """
    Update user-specific job status in user_job_matches table

    Args:
        user_id: User ID
        job_id: Job ID (database primary key, not job_id string)
        status: New status ('shortlisted', 'deleted', 'viewed', 'applying', 'applied')
        notes: Optional notes
    """
    conn = self._get_connection()
    try:
        cursor = conn.cursor()

        # Check if user_job_match exists
        cursor.execute("""
            SELECT id FROM user_job_matches
            WHERE user_id = %s AND job_id = %s
        """, (user_id, job_id))

        match_row = cursor.fetchone()

        if match_row:
            # Update existing record
            if notes:
                cursor.execute("""
                    UPDATE user_job_matches
                    SET status = %s, last_updated = NOW()
                    WHERE user_id = %s AND job_id = %s
                """, (status, user_id, job_id))
            else:
                cursor.execute("""
                    UPDATE user_job_matches
                    SET status = %s, last_updated = NOW()
                    WHERE user_id = %s AND job_id = %s
                """, (status, user_id, job_id))
        else:
            # Create new record (shouldn't happen in normal flow, but handle it)
            cursor.execute("""
                INSERT INTO user_job_matches
                (user_id, job_id, status, created_date, last_updated)
                VALUES (%s, %s, %s, NOW(), NOW())
            """, (user_id, job_id, status))

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating user job status: {e}")
        raise
    finally:
        cursor.close()
        self._return_connection(conn)
```

---

### Fix #3: Update Route Handlers

**File:** `app.py`

```python
@app.route('/jobs/<int:job_id>/shortlist', methods=['POST'])
@login_required
def shortlist_job(job_id):
    """Add job to shortlist"""
    try:
        user_id = get_user_id()  # Get current user ID
        job_db.update_user_job_status(user_id, job_id, 'shortlisted')
        flash('Job added to your dashboard!', 'success')
    except Exception as e:
        flash(f'Error adding job to shortlist: {str(e)}', 'error')

    return redirect(request.referrer or url_for('jobs'))


@app.route('/jobs/<int:job_id>/remove-shortlist', methods=['POST'])
@login_required
def remove_shortlist(job_id):
    """Remove job from shortlist"""
    try:
        user_id = get_user_id()
        job_db.update_user_job_status(user_id, job_id, 'viewed')
        flash('Job removed from dashboard', 'info')
    except Exception as e:
        flash(f'Error removing job: {str(e)}', 'error')

    return redirect(request.referrer or url_for('dashboard'))


@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    """Hide job permanently for this user"""
    try:
        user_id = get_user_id()
        job_db.update_user_job_status(user_id, job_id, 'deleted')
        flash('Job hidden - it will not appear in future searches', 'success')
    except Exception as e:
        flash(f'Error deleting job: {str(e)}', 'error')

    return redirect(request.referrer or url_for('jobs'))
```

**Changes:**
1. Get `user_id` from current session using `get_user_id()`
2. Call `update_user_job_status()` instead of `update_job_status()`
3. Pass `user_id` and `job_id` to ensure user-specific updates

---

### Fix #4: Update Other Affected Methods

These methods also need user filtering:

**File:** `src/database/postgres_operations.py`

```python
# Already correct - uses user_id parameter properly
def get_unfiltered_jobs_for_user(self, user_id: int) -> List[Dict]:
    """Get jobs that haven't been matched/filtered for this user yet"""
    # ... implementation already uses user_id correctly

# Needs fix
def get_deleted_job_ids(self) -> set:
    """Get set of job_ids that have been deleted by ANY user"""
    # Current: Returns ALL deleted jobs globally
    # Should return: User-specific deleted jobs
```

**New method:**
```python
def get_deleted_job_ids_for_user(self, user_id: int) -> set:
    """
    Get job IDs that have been deleted by specific user

    Args:
        user_id: User ID

    Returns:
        Set of job IDs (database primary keys) deleted by this user
    """
    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_id FROM user_job_matches
            WHERE user_id = %s AND status = 'deleted'
        """, (user_id,))
        deleted_ids = {row[0] for row in cursor.fetchall()}
        return deleted_ids
    finally:
        cursor.close()
        self._return_connection(conn)
```

---

## Testing Plan

### 1. Test User Isolation

```python
# Create two test users
user_a_id = 1
user_b_id = 2
job_id = 100

# User A shortcuts job
db.update_user_job_status(user_a_id, job_id, 'shortlisted')

# User A should see job
jobs_a = db.get_shortlisted_jobs('user_a@test.com')
assert job_id in [j['id'] for j in jobs_a]

# User B should NOT see job
jobs_b = db.get_shortlisted_jobs('user_b@test.com')
assert job_id not in [j['id'] for j in jobs_b]
```

### 2. Test Status Updates

```python
# User A shortcuts job
db.update_user_job_status(user_a_id, job_id, 'shortlisted')

# User B deletes same job
db.update_user_job_status(user_b_id, job_id, 'deleted')

# User A should still see it as shortlisted
jobs_a = db.get_shortlisted_jobs('user_a@test.com')
assert job_id in [j['id'] for j in jobs_a]

# User B should NOT see it (deleted)
jobs_b = db.get_shortlisted_jobs('user_b@test.com')
assert job_id not in [j['id'] for j in jobs_b]
```

### 3. Integration Test

```bash
# Login as User A
# Shortlist a job
# Check dashboard - should show job

# Login as User B (different browser/incognito)
# Check dashboard - should NOT show User A's job
# Shortlist different job
# Check dashboard - should show only own job

# Login as User A again
# Check dashboard - should still show original job
# Should NOT show User B's job
```

---

## Affected Areas

### Database Operations
- ✅ `get_shortlisted_jobs()` - Missing user filter
- ✅ `update_job_status()` - Updates wrong table
- ⚠️ `get_deleted_job_ids()` - Returns all users' deleted jobs
- ⚠️ `get_user_feedback()` - Check if it filters by user

### Route Handlers
- ✅ `/jobs/<int:job_id>/shortlist` - Uses global status
- ✅ `/jobs/<int:job_id>/remove-shortlist` - Uses global status
- ✅ `/jobs/<int:job_id>/delete` - Uses global status
- ⚠️ `/jobs` route - May need to exclude user's deleted jobs
- ⚠️ `/dashboard` route - Already calls get_shortlisted_jobs()

### Templates
- ✅ `dashboard.html` - Should work after backend fix
- ⚠️ `jobs.html` - Check if deleted jobs are filtered

---

## Migration Plan

### Step 1: Add User-Specific Methods (Non-Breaking)
1. Create `update_user_job_status()` method
2. Create `get_deleted_job_ids_for_user()` method
3. Update `get_shortlisted_jobs()` to use user filtering
4. Deploy to production

### Step 2: Update Route Handlers
1. Update all job action routes to use new methods
2. Add `@login_required` decorators if missing
3. Test in staging
4. Deploy to production

### Step 3: Clean Up Old Methods
1. Deprecate `update_job_status()` for user actions
2. Keep it only for system-level status changes
3. Update documentation

### Step 4: Data Cleanup (Optional)
1. Review existing `jobs.status` values
2. Migrate to `user_job_matches.status` if needed
3. Reset global `jobs.status` to 'active'

---

## Priority

**CRITICAL** - This should be fixed immediately before adding more users to production.

---

## Related Files

- `src/database/postgres_operations.py` - Database methods
- `src/database/postgres_cv_operations.py` - CV manager (uses same methods)
- `app.py` - Route handlers
- `web/templates/dashboard.html` - Dashboard UI
- `web/templates/jobs.html` - Job listing UI

---

## Notes

- The `user_job_matches` table architecture is **correct**
- The bug is in the **implementation**, not the design
- Fix is straightforward: use existing `user_job_matches.status` instead of `jobs.status`
- No database schema changes needed
- Minimal code changes required

---

## Next Steps

1. **Immediate:** Warn users about privacy issue if multiple users exist
2. **High Priority:** Implement fixes outlined above
3. **Testing:** Run comprehensive user isolation tests
4. **Documentation:** Update API docs with correct usage
5. **Monitoring:** Add logging to track user-specific actions
