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
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from django.utils import timezone
from datetime import timedelta

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
        self.assertEqual(decoded['user_id'],str(self.user.pk))

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

# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Feature 3 — Current User Profile Tests
# ═══════════════════════════════════════════════════════════════════════════════

class CurrentUserProfileTests(APITestCase):
    """
    Test suite for GET /api/v1/auth/me/
    """
    client: APIClient

    def setUp(self):
        """
        Create a user and generate a valid token for authentication.
        """
        self.me_url = '/api/v1/auth/me/'
        self.user = User.objects.create_user(
            username='sarah@example.com',
            email='sarah@example.com',
            password='SecurePass123!',
            first_name='Sarah',
            last_name='Johnson'
        )
        # Generate a valid access token for this user
        # AccessToken is a SimpleJWT class that creates a signed JWT
        self.access_token = str(AccessToken.for_user(self.user))

    def get_json(self, url: str) -> tuple[Response, dict[str, Any]]:
        """
        Typed wrapper around self.client.get. Every raw self.client.get()
        call risks Pyright resolving to a stub overload that isn't DRF's
        Response (HttpResponse, WSGIRequest, etc., depending on context) —
        so ALL GET calls in this class must go through here, never direct.
        """
        response = cast(Response, self.client.get(url))
        response_data = response.data
        assert response_data is not None, 'Expected response.data to be present'
        return response, cast(dict[str, Any], response_data)

    def patch_json(self, url: str, data: dict[str, Any]) -> Response:
        """
        Typed wrapper around self.client.patch. Same rationale as get_json —
        avoids raw self.client.patch() calls that the stubs mis-resolve.
        """
        return cast(Response, self.client.patch(url, data=data, format='json'))

    def _authorize_client(self):
        """
        Helper method to attach the Authorization header to the test client.
        We use this in every test that requires authentication.
        """
        self.client.credentials(
            HTTP_AUTHORIZATION=F'Bearer {self.access_token}'
        )

    # ─────────────────────────────────────────────────────────────
    # SUCCESS CASES
    # ─────────────────────────────────────────────────────────────
    def test_authenticated_user_can_view_profile(self):
        """
        Given a valid access token,
        When GET /me/ is called with Authorization header,
        Then 200 OK is returned with the user's profile.
        """
        self._authorize_client()
        response, data = self.get_json(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['id'], self.user.pk)
        self.assertEqual(data['email'], 'sarah@example.com')
        self.assertEqual(data['first_name'], 'Sarah')
        self.assertEqual(data['last_name'], 'Johnson')
        self.assertIn('date_joined', data)

    def test_profile_response_does_not_contain_password(self):
        """
        Security: The profile response must never contain password
        or any authentication-related fields.
        """
        self._authorize_client()
        response, data = self.get_json(self.me_url)
        self.assertNotIn('password', data)
        self.assertNotIn('username', data)  # Internal field, not API-relevant

    def test_profile_fields_are_read_only(self):
        """
        Given an authenticated GET request,
        The serializer should not allow modifications through this endpoint.
        (This is tested implicitly: RetrieveAPIView only supports GET,
        but we also verify the serializer's read_only_fields.)
        """
        self._authorize_client()

        # Attempting to PATCH /me/ should fail because RetrieveAPIView
        # does not support PATCH. This tests our endpoint is truly read-only.
        response = self.patch_json(
            self.me_url,
            data={'first_name': 'Hacked'},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # ─────────────────────────────────────────────────────────────
    # AUTHENTICATION FAILURE CASES
    # ─────────────────────────────────────────────────────────────
    def test_unauthenticated_request_rejected(self):
        """
        Given no Authorization header,
        When GET /me/ is called,
        Then 401 Unauthorized is returned.
        """
        # Explicitly clear any credentials
        self.client.credentials()

        response, data = self.get_json(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', data)

    def test_invalid_token_rejected(self):
        """
        Given a malformed or forged token,
        When GET /me/ is called,
        Then 401 Unauthorized is returned.
        """
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer invalid.token.here'
        )
        response, data = self.get_json(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_token_rejected(self):
        """
        Given a token that has passed its expiration time,
        When GET /me/ is called,
        Then 401 Unauthorized is returned.

        We create a token with a backdated 'exp' claim to simulate expiry.
        """
        # Create a token that expired 1 hour ago
        token = AccessToken.for_user(self.user)
        token.set_exp(from_time=timezone.now() - timedelta(hours=2))
        expired_token = str(token)

        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {expired_token}'
        )

        response, data = self.get_json(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_for_deleted_user_rejected(self):
        """
        Given a token was issued to a user who has since been deleted,
        When GET /me/ is called,
        Then 401 Unauthorized is returned.

        This tests the database round-trip: JWTAuthentication decodes the
        token successfully, but the user lookup fails.
        """
        # Create a temporary user and token
        temp_user = User.objects.create_user(
            username='temp@example.com',
            email='temp@example.com',
            password='TempPass123!'
        )
        temp_token = str(AccessToken.for_user(temp_user))
        # Delete the user (simulating admin deletion)
        temp_user.delete()

        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {temp_token}'
        )

        response, data = self.get_json(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_for_inactive_user_rejected(self):
        """
        Given a valid token for a user who has been deactivated (is_active=False),
        When GET /me/ is called,
        Then 401 Unauthorized is returned.
        """
        # Deactivate the main test user
        self.user.is_active = False
        self.user.save()

        self._authorize_client()

        response, data = self.get_json(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ─────────────────────────────────────────────────────────────
    # EDGE CASES
    # ─────────────────────────────────────────────────────────────
    def test_missing_bearer_prefix_rejected(self):
        """
        Given a token without the 'Bearer ' prefix,
        When GET /me/ is called,
        Then 401 Unauthorized is returned.

        DRF's JWTAuthentication expects the exact format: Bearer <token>
        """
        self.client.credentials(
            HTTP_AUTHORIZATION=f'{self.access_token}'  # No "Bearer " prefix
        )
        response, data = self.get_json(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_authorization_header_rejected(self):
        """
        Given an empty Authorization header,
        Then 401 Unauthorized is returned.
        """
        self.client.credentials(HTTP_AUTHORIZATION='')

        response, data = self.get_json(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
