#!/bin/bash
set -e

# Activate virtual environment
. /opt/venv/bin/activate

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --no-input