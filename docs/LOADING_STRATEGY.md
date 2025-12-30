# Job Loading Strategy - Quota Management

**Ultra Plan Quota:** 20,000 jobs/month, 10,000 requests/month

⚠️ **IMPORTANT:** Backfilling COUNTS towards your monthly quota!
Source: [Active Jobs DB API Documentation](https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/active-jobs-db)

---

## Recommended Strategy

### Phase 1: Initial Database Build (First Day of Month)

**Run ONE backfill at the start of the month:**

```bash
# 1. Enable backfill in config.yaml
# Set backfill.enabled: true

# 2. Review quota calculation in config.yaml
# Current settings will use ~16,000 jobs (80% of quota)

# 3. Run backfill
python scripts/daily_job_loader.py --backfill
```

**Expected Result:**
- 10,000-16,000 jobs loaded (7 days of history)
- 80% of monthly quota consumed
- 4,000-10,000 jobs remaining for daily updates

### Phase 2: Daily Updates (Rest of Month)

**Run daily updates every 24 hours:**

```bash
# Disable backfill in config.yaml
# Set backfill.enabled: false

# Run daily (via cron or manual)
python scripts/daily_job_loader.py
```

**Expected Result:**
- 100-500 jobs/day (actual, not max)
- ~3,000-15,000 jobs/month
- Well within remaining quota

---

## Quota Calculations

### Backfill (Week)
```
Strategy 1: Key Cities
  5 cities × 20 pages × 100 jobs/page = 10,000 jobs

Strategy 2: Flexible Work
  3 work types × 20 pages × 100 jobs/page = 6,000 jobs

Total: ~16,000 jobs (80% of quota)
```

### Daily Loading (24h)
```
Strategy 1: Key Cities
  2 cities × 10 pages × 100 jobs/page = 2,000 jobs MAX
  (Reality: ~50-200 jobs actual)

Strategy 2: Flexible Work
  3 work types × 10 pages × 100 jobs/page = 3,000 jobs MAX
  (Reality: ~50-300 jobs actual)

Total per day: ~100-500 jobs (actual usage)
Monthly: ~3,000-15,000 jobs
```

---

## Adding New Cities

When a user from Frankfurt joins:

1. **Open `config.yaml`**
2. **Add to daily_loading.key_cities:**
   ```yaml
   key_cities:
     - "Berlin"
     - "Hamburg"
     - "Frankfurt"  # ← Add here
   ```
3. **Run next daily update** - Frankfurt jobs automatically included
4. **Optional:** Run backfill if you need historical Frankfurt jobs

---

## Quota Management Tips

### 1. Monitor Actual Usage
The script shows actual quota consumption after each run:
```
Quota Analysis (Ultra Plan: 20,000 jobs/month):
  This run used: 487 jobs (2.4% of monthly quota)
  Projected monthly: 487/day × 30 = 14,610 jobs/month
  ✓ Good! Projected 73% quota utilization
```

### 2. Adjust max_pages_per_query
If projected usage exceeds quota:

**config.yaml:**
```yaml
daily_loading:
  max_pages_per_query: 5  # Reduce from 10 to 5
```

### 3. Use API-Level Filters
Always use AI filters at API level (not local filtering):
- Fetches only relevant jobs
- Saves quota on irrelevant jobs
- Already implemented in the loader!

### 4. Strategic City Selection
Only add cities where you have users:
- Don't fetch Munich jobs if no users there
- Add cities incrementally as user base grows

---

## Troubleshooting

### Quota Exceeded
```
Error: Monthly quota exceeded (20,000 jobs)
```

**Solutions:**
1. Wait until next month for quota reset
2. Reduce `max_pages_per_query` in config.yaml
3. Remove cities without active users
4. Contact Active Jobs DB for quota upgrade

### Too Few Jobs
```
Only 50 jobs fetched today, expecting more
```

**Possible Reasons:**
1. Using 24h filter - fewer new jobs posted
2. API filters too restrictive
3. Normal variance - job posting isn't constant

**Solutions:**
- Check if it's weekend (fewer postings)
- Review AI filters in config.yaml
- Run manual check with wider filters

### Duplicate Jobs
```
Duplicates skipped: 234
```

This is **NORMAL** and **GOOD**:
- Hamburg jobs may overlap with Germany-wide remote jobs
- Script automatically deduplicates
- Shows efficient quota usage

---

## Best Practices

✅ **DO:**
- Run backfill ONCE at month start
- Use daily updates (24h) for ongoing collection
- Monitor actual quota usage weekly
- Add cities only when users join from there
- Keep backfill disabled by default

❌ **DON'T:**
- Run backfill multiple times per month
- Use "week" filter for daily updates
- Fetch cities without users
- Ignore quota warnings
- Disable deduplication

---

## Automation (Cron)

Add to crontab for daily execution:

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/job-monitor && /path/to/python scripts/daily_job_loader.py >> logs/daily_loader.log 2>&1
```

---

## Monthly Checklist

**Start of Month:**
- [ ] Review user locations
- [ ] Update config.yaml with new cities if needed
- [ ] Enable backfill in config.yaml
- [ ] Run backfill once
- [ ] Disable backfill immediately after
- [ ] Check quota usage from backfill

**During Month:**
- [ ] Daily updates run automatically
- [ ] Monitor quota usage weekly
- [ ] Adjust max_pages if needed
- [ ] Add new cities as users join

**End of Month:**
- [ ] Review total quota usage
- [ ] Check job coverage by city
- [ ] Plan adjustments for next month
