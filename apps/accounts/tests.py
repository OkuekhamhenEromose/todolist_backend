"""
Tests for the accounts app.

We use Django REST Framework's APITestCase because it provides:
- APIClient: A test client that speaks HTTP and JSON
- Built-in assertion methods for HTTP status codes
- Automatic database rollback between tests (each test starts fresh)
"""

from typing import Any, cast

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.response import Response

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
