"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""
# wsgi.py is used for deployment or production because when gunicorn serves your app, you are in production. It tells the web server how to interact with the Django application. It sets the DJANGO_SETTINGS_MODULE environment variable to point to the settings module, and then it creates a WSGI application object that the web server can use to forward requests to Django.
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
