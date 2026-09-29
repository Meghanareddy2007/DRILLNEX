web: gunicorn --chdir backend --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --worker-class gthread --timeout 120 app:app
