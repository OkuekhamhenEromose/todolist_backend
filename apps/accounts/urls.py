"""
URL configuration for the accounts app.

These URLs are included under /api/v1/auth/ via config/urls.py
"""
from django.urls import path
# Added for registration feature
from .views import RegisterView
# Added for login feature
from .views import LoginView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # path(route, view, name)
    # route: The URL pattern relative to the app prefix
    # view: The view class (must call .as_view() for CBVs)
    # name: A unique identifier for reverse URL lookups
    path('register/', RegisterView.as_view(), name='register'),
     # Feature 2: Login (returns access + refresh tokens)
    path('login/', LoginView.as_view(), name='login'),
    # Feature 2: Token Refresh (returns new access token)
    # We use SimpleJWT's built-in view with no customization for MVP.
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
