# Railway Procfile - Defines service types
# Railway will use this to identify web and worker processes

web: gunicorn app:app --bind 0.0.0.0:$PORT
cron: python scripts/daily_job_cron.py --schedule "6:00"
