from .base import *

DEBUG = False

# In production, ALLOWED_HOSTS comes from environment
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Security headers (only when HTTPS is configured)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# Why are some security settings commented out?
# SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, and CSRF_COOKIE_SECURE require HTTPS. During development on localhost, you don't have HTTPS. Uncomment these when you deploy with SSL certificates.
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Production logging: write to file
LOGGING['loggers']['django']['handlers'] = ['file']
LOGGING['root']['handlers'] = ['file']

# Performance: persistent database connections
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes