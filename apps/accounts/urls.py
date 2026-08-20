"""
URL configuration for the accounts app.

These URLs are included under /api/v1/auth/ via config/urls.py
"""
from django.urls import path
from .views import RegisterView

urlpatterns = [
    # path(route, view, name)
    # route: The URL pattern relative to the app prefix
    # view: The view class (must call .as_view() for CBVs)
    # name: A unique identifier for reverse URL lookups
    path('register/', RegisterView.as_view(), name='register'),
]

