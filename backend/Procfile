# Railway Procfile - Defines service types
# Railway will use this to identify web and worker processes

web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
cron: python scripts/daily_job_cron.py --interval 1440
