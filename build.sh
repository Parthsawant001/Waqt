#!/usr/bin/env bash
set -o errexit

echo "Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Collect static files for production (WhiteNoise)
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate --no-input

echo "Build complete."
