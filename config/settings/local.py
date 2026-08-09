from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Database uses the same PostgreSQL instance
# (In local.py, we could override to SQLite for quick tests, but we use PostgreSQL
#  to ensure "it works on my machine" actually means "it works in production")

# Development logging: verbose to console
LOGGING['loggers']['django']['handlers'] = ['console']
LOGGING['loggers']['django']['level'] = 'DEBUG'

# Enable Django Debug Toolbar (we'll configure this in Phase 7)
# INTERNAL_IPS = ['127.0.0.1']

# Email backend for development (prints to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'