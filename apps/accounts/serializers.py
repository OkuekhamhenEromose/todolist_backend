"""
Serializers for the accounts app.
A serializer in Django REST Framework is like a translator between:
- Python objects (Django models) and JSON (for API responses)
- JSON (from API requests) and Python objects (for validation and creation)
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User

# get_user_model() returns our custom User model (apps.accounts.models.User)
# We use this instead of importing directly because it respects AUTH_USER_MODEL
User = get_user_model

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Handles:
    - Validating email uniqueness
    - Validating password strength using Django's built-in validators
    - Creating the user with a hashed password
    - Auto-setting username to email (since our API is email-centric)
    """
    # We explicitly declare the password field so we can add validators
    # and mark it as write_only (never returned in responses)
    password = serializers.CharField(
        write_only=True,           # Password is accepted in requests but never sent back
        required=True,             # Must be provided
        validators=[validate_password]  # Uses Django's password validation (min length, not common, etc.)
    )
    class Meta:
        """
        Meta class configures the serializer's behavior.
        """
        model = User # This serializer works with the User model
        fields = [ # Only these fields are accepted/returned
            'id',
            'email',
            'password',
            'first_name',
            'last_name',
            'date_joined',
        ]
        read_only_fields = [ # These fields are auto-generated; client cannot set them
            'id',
            'date_joined',
        ]

    def create(self, validated_data):
        """
        Called when serializer.save() is invoked.

        We override the default create because:
        1. We need to extract the password and hash it (not store plain text)
        2. We need to set username = email (our User model uses AbstractUser which requires username)
        3. Django's create_user() handles password hashing automatically
        """
        # Extract password from validated data
        password = validated_data.pop('password')

        # Extract email to use as username
        email = validated_data.pop('email')

        # create_user() is the SAFE way to create users in Django.
        # It automatically:
        # - Hashes the password using the configured hasher (PBKDF2/Argon2)
        # - Sets is_active = True
        # - Saves the user to the database
        user = User.objects.create_user(
            username=email,        # AbstractUser requires username; we use email
            email=email,
            password=password,     # create_user hashes this automatically
            **validated_data       # first_name, last_name, etc.
        )
        return user
