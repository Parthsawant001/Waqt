import os

with open('waqt_project/settings.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add WhiteNoise
if 'WhiteNoiseMiddleware' not in content:
    content = content.replace(
        "'django.middleware.security.SecurityMiddleware',",
        "'django.middleware.security.SecurityMiddleware',\n    'whitenoise.middleware.WhiteNoiseMiddleware',"
    )

# Add STATIC_ROOT
if 'STATIC_ROOT' not in content:
    content = content.replace(
        "STATIC_URL = 'static/'",
        "STATIC_URL = 'static/'\nSTATIC_ROOT = BASE_DIR / 'staticfiles'"
    )

# Fix DEBUG and ALLOWED_HOSTS if needed
if "ALLOWED_HOSTS = ['localhost', '127.0.0.1']" in content:
    content = content.replace(
        "ALLOWED_HOSTS = ['localhost', '127.0.0.1']",
        "ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')"
    )
    content = content.replace(
        "DEBUG = True",
        "DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'"
    )

with open('waqt_project/settings.py', 'w', encoding='utf-8') as f:
    f.write(content)
