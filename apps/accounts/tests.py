"""
Tests for the accounts app.

We use Django REST Framework's APITestCase because it provides:
- APIClient: A test client that speaks HTTP and JSON
- Built-in assertion methods for HTTP status codes
- Automatic database rollback between tests (each test starts fresh)
"""

from typing import Any, cast
from urllib import response

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class UserRegistrationTests(APITestCase):
    """
    Test suite for the POST /api/v1/auth/register/ endpoint.
    """

    def setUp(self):
        """
        setUp runs before EVERY test method.
        We define common data here to avoid repetition (DRY principle).
        """
        self.register_url = '/api/v1/auth/register/'
        self.valid_payload = {
            'email': 'sarah@example.com',
            'password': 'SecurePass123!',
            'first_name': 'Sarah',
            'last_name': 'Johnson'
        }

    def post_json(self, url: str, data: dict[str, Any]) -> tuple[Response, dict[str, Any]]:
        """
        Typed wrapper around self.client.post.

        Returns both the response AND its `.data` pre-extracted as a plain,
        guaranteed-non-None dict. We extract `.data` here (rather than relying
        on callers to narrow it themselves) because narrowing performed inside
        this function does not persist on `response.data` once control
        returns to the caller — Pyright resets to the stub's declared
        `ReturnDict | None` type at each new attribute access. Pulling it into
        a local variable and returning that variable preserves the narrowed,
        non-Optional type for the caller.
        """
        response = cast(Response, self.client.post(url, data=data, format='json'))
        response_data = response.data
        assert response_data is not None, 'Expected response.data to be present'
        return response, cast(dict[str, Any], response_data)

    # ─────────────────────────────────────────────────────────────
    # SUCCESS CASES
    # ─────────────────────────────────────────────────────────────

    def test_successful_registration(self):
        """
        Given valid registration data,
        When POST /api/v1/auth/register/ is called,
        Then a user is created and 201 is returned with user data.
        """
        response, data = self.post_json(self.register_url, self.valid_payload)

        # Assert status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert database state
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        if user is None:
            self.fail('User was not created')

        self.assertEqual(user.email, 'sarah@example.com')
        self.assertEqual(user.username, 'sarah@example.com')  # Auto-set

        # Assert response data
        self.assertEqual(data['email'], 'sarah@example.com')
        self.assertEqual(data['first_name'], 'Sarah')
        self.assertIn('id', data)
        self.assertIn('date_joined', data)

        # Security: Password must NOT appear in response
        self.assertNotIn('password', data)

        # Security: Password must be hashed in database
        self.assertNotEqual(user.password, 'SecurePass123!')
        self.assertTrue(user.check_password('SecurePass123!'))

    def test_registration_without_optional_fields(self):
        """
        first_name and last_name are optional.
        The serializer should accept missing optional fields.
        """
        payload = {
            'email': 'marcus@example.com',
            'password': 'AnotherPass123!'
        }
        response, data = self.post_json(self.register_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')

    # ─────────────────────────────────────────────────────────────
    # VALIDATION FAILURE CASES
    # ─────────────────────────────────────────────────────────────

    def test_duplicate_email_rejected(self):
        """
        Given a user already exists with email sarah@example.com,
        When another registration uses the same email,
        Then 400 Bad Request is returned with an email error.
        """
        # Create existing user
        User.objects.create_user(
            username='sarah@example.com',
            email='sarah@example.com',
            password='SomePass123!'
        )

        response, data = self.post_json(self.register_url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', data)

    def test_weak_password_rejected(self):
        """
        Given a password that is too short,
        When registration is attempted,
        Then 400 Bad Request is returned with a password error.
        """
        payload = self.valid_payload.copy()
        payload['password'] = '123'  # Too short, too simple

        response, data = self.post_json(self.register_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', data)

    def test_common_password_rejected(self):
        """
        Given a password that is in Django's common password list,
        When registration is attempted,
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        payload['password'] = 'password123'  # In Django's common password list

        response, data = self.post_json(self.register_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', data)

    def test_missing_email_rejected(self):
        """
        Given no email in the request,
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        del payload['email']

        response, data = self.post_json(self.register_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', data)

    def test_missing_password_rejected(self):
        """
        Given no password in the request,
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        del payload['password']

        response, data = self.post_json(self.register_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', data)

    def test_invalid_email_format_rejected(self):
        """
        Given an email without @ symbol,
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        payload['email'] = 'not-an-email'

        response, data = self.post_json(self.register_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', data)

    # ─────────────────────────────────────────────────────────────
    # EDGE CASES
    # ─────────────────────────────────────────────────────────────

    def test_numeric_password_rejected(self):
        """
        Django's NumericPasswordValidator rejects entirely numeric passwords.
        """
        payload = self.valid_payload.copy()
        payload['password'] = '12345678'

        response, data = self.post_json(self.register_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', data)

# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Feature 2 — Login Tests
# ═══════════════════════════════════════════════════════════════════════════════

class UserLoginTests(APITestCase):
    """
    Test suite for POST /api/v1/auth/login/ and POST /api/v1/auth/token/refresh/
    """
    def setUp(self):
        """
        Create a user that we can log in with.
        Runs before every test method.
        """
        self.login_url = '/api/v1/auth/login/'
        self.refresh_url = '/api/v1/auth/token/refresh/'

        """
        Create a user that we can log in with.
        Runs before every test method.
        """
        self.user = User.objects.create_user(
            username='sarah@example.com',
            email='sarah@example.com',
            password='SecurePass123!',
            first_name='Sarah',
            last_name='Johnson'
        )

        self.valid_credentials = {
            'email': 'sarah@example.com',
            'password': 'SecurePass123!'
        }

    def post_json(self, url: str, data: dict[str, Any]) -> tuple[Response, dict[str, Any]]:
        """
        Typed wrapper around self.client.post.

        Same rationale as UserRegistrationTests.post_json: self.client.post()
        is typed by the Django/DRF stubs as returning HttpResponse, which has
        no `.data` attribute. Casting to DRF's Response and extracting `.data`
        into a local variable here gives callers a properly typed, non-Optional
        dict instead of triggering "Cannot access attribute 'data' for class
        'HttpResponse'" under Pyright.
        """
        response = cast(Response, self.client.post(url, data=data, format='json'))
        response_data = response.data
        assert response_data is not None, 'Expected response.data to be present'
        return response, cast(dict[str, Any], response_data)

        # ─────────────────────────────────────────────────────────────
    # SUCCESS CASES
    # ─────────────────────────────────────────────────────────────
    def test_successful_login_returns_tokens(self):
        """
        Given valid email and password,
        When POST /login/ is called,
        Then 200 OK is returned with both refresh and access tokens.
        """
        response, data = self.post_json(self.login_url, self.valid_credentials)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', data)
        self.assertIn('refresh', data)

        # Both tokens should be non-empty strings
        self.assertIsInstance(data['access'], str)
        self.assertIsInstance(data['refresh'], str)
        self.assertTrue(len(data['access']) > 0)
        self.assertTrue(len(data['refresh']) > 0)

    def test_access_token_contains_user_id(self):
        """
        The access token payload must contain the user's id for downstream
        identification in protected endpoints (e.g., "show MY tasks").
        """
        response, data = self.post_json(self.login_url, self.valid_credentials)
        access_token = data['access']
        decoded = AccessToken(access_token)
        # Our settings.py configured USER_ID_CLAIM = 'user_id'
        self.assertIn('user_id', decoded)
        self.assertEqual(decoded['user_id'], self.user.pk)

    def test_successful_login_does_not_expose_password(self):
        """
        Security: The login response must never contain the password
        or any password-related fields.
        """
        response, data = self.post_json(self.login_url, self.valid_credentials)
        self.assertNotIn('password', data)

    # ─────────────────────────────────────────────────────────────
    # AUTHENTICATION FAILURE CASES
    # ─────────────────────────────────────────────────────────────
    def test_login_with_wrong_password(self):
        """
        Given a valid email but incorrect password,
        When POST /login/ is called,
        Then 401 Unauthorized is returned.

        Security: The error message must be identical to the "user not found"
        case to prevent email enumeration attacks.
        """
        payload = {
            'email': 'sarah@example.com',
            'password': 'WrongPassword123!'
        }
        response, data = self.post_json(self.login_url, payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', data)

    def test_login_with_nonexistent_email(self):
        """
        Given an email that does not exist in the database,
        When POST /login/ is called,
        Then 401 Unauthorized is returned with the SAME error message
        as the wrong-password case.
        """
        payload = {
            'email': 'nobody@example.com',
            'password': 'SomePassword123!'
        }
        response, data = self.post_json(self.login_url, payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', data)

    def test_login_with_inactive_user(self):
        """
        Given a user exists but is_active=False,
        When POST /login/ is called,
        Then 401 Unauthorized is returned.
        """
        # Deactivate the user
        self.user.is_active = False
        self.user.save()

        response, data = self.post_json(self.login_url, self.valid_credentials)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ─────────────────────────────────────────────────────────────
    # VALIDATION FAILURE CASES
    # ─────────────────────────────────────────────────────────────

    def test_login_missing_email(self):
        """
        Given no email field in the request,
        Then 400 Bad Request is returned.
        """
        payload = {'password': 'SecurePass123!'}
        response, data = self.post_json(self.login_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', data)

    def test_login_missing_password(self):
        """
        Given no password field in the request,
        Then 400 Bad Request is returned.
        """
        payload = {'email': 'sarah@example.com'}
        response, data = self.post_json(self.login_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', data)

    # ─────────────────────────────────────────────────────────────
    # TOKEN REFRESH CASES
    # ─────────────────────────────────────────────────────────────

    def test_token_refresh_with_valid_refresh_token(self):
        """
        Given a valid refresh token from login,
        When POST /token/refresh/ is called,
        Then a new access token is returned.
        """
        # First, log in to get tokens
        login_response, login_data = self.post_json(self.login_url, self.valid_credentials)
        refresh_token = login_data['refresh']

        # Now refresh
        response, data = self.post_json(self.refresh_url, {'refresh': refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', data)
        # The new access token should be different from the old one
        self.assertNotEqual(data['access'], login_data['access'])

    def test_token_refresh_with_invalid_token(self):
        """
        Given an invalid or expired refresh token,
        When POST /token/refresh/ is called,
        Then 401 Unauthorized is returned.
        """
        response, data = self.post_json(self.refresh_url, {'refresh': 'invalid.token.here'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
