"""
WSGI config for waqt_project project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waqt_project.settings')

application = get_wsgi_application()

# Expose app for serverless platforms (e.g., Vercel)
app = application
