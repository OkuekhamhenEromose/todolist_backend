"""
Views for the accounts app.

In Django REST Framework, a view is a Python function or class that receives
an HTTP request and returns an HTTP response. Class-based views (CBVs) are
preferred for APIs because they provide reusable patterns.
"""
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import User

from .serializers import UserRegistrationSerializer

# Create your views here.
User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration.

    POST /api/v1/auth/register/

    Accepts: email, password, first_name, last_name
    Returns: User object (201 Created) or validation errors (400 Bad Request)

    Why CreateAPIView?
    - It handles POST requests
    - It automatically validates using the serializer
    - It returns 201 status on success
    - It provides proper error responses on validation failure
    """

    # Queryset is used by the serializer for uniqueness checks
    # and by the browsable API. It does NOT expose a list endpoint.
    queryset = User.objects.all()

    # The serializer class handles validation and object creation
    serializer_class = UserRegistrationSerializer

    # AllowAny means no authentication is required to access this endpoint
    # This is correct because you can't be logged in before you register
    permission_classes = [AllowAny]
