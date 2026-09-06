"""
Tests for the todos app.
"""

from typing import Any, cast
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from .models import Task

# Create your tests here.

User = get_user_model()

class TaskCreateTests(APITestCase):
    """
    Test suite for POST /api/v1/todos/ (Task Creation)
    """
    client: APIClient

    def setUp(self):
        self.create_url = '/api/v1/todos/'

        self.user = User.objects.create_user(
            username='sarah@example.com',
            email='sarah@example.com',
            password='SecurePass123!'
        )

        # Generate token and authenticate client
        self.access_token = str(AccessToken.for_user(self.user))
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )

        self.valid_payload: dict[str, Any] = {
            'title': 'Submit Q3 report',
            'description': 'Prepare slides and send to manager',
            'priority': 'high',
            'category': 'work',
            'due_date': '2026-08-15'
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

    def _get_first_task(self) -> Task:
        """
        Helper to fetch Task.objects.first() with a None-guard, since the
        stubs type .first() as Task | None. Every test that needs to
        inspect the created task's fields should go through this instead
        of calling Task.objects.first() directly, to avoid "possibly None"
        attribute-access errors under Pyright.
        """
        task = Task.objects.first()
        if task is None:
            self.fail('Task was not created')
        return task

    def test_authenticated_user_can_create_task(self):
        """
        Given valid task data and valid auth token,
        When POST /todos/ is called,
        Then 201 Created is returned and task exists in DB.
        """
        response, data = self.post_json(self.create_url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 1)

        task = self._get_first_task()
        self.assertEqual(task.title, 'Submit Q3 report')
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.status, 'pending')  # Default
        self.assertEqual(task.priority, 'high')
        self.assertEqual(task.category, 'work')

    def test_user_auto_assigned_from_token(self):
        """
        Security: The client cannot specify another user_id.
        The view must ignore a malicious 'user' field and use request.user.
        """
        payload = self.valid_payload.copy()
        payload['user'] = 99999  # Attempt to assign to non-existent user

        response, data = self.post_json(
            self.create_url,
            payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = self._get_first_task()
        self.assertEqual(task.user, self.user)  # Ignored the injected user_id

    def test_unauthenticated_request_rejected(self):
        """
        Given no Authorization header,
        Then 401 Unauthorized is returned.
        """
        self.client.credentials()  # Clear auth

        response, data = self.post_json(
            self.create_url,
            data=self.valid_payload,
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_title_rejected(self):
        """
        Given no title in request,
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        del payload['title']

        response, data = self.post_json(self.create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', data)

    def test_whitespace_only_title_rejected(self):
        """
        Given title with only spaces,
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        payload['title'] = '     '

        response, data = self.post_json(self.create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', data)

    def test_invalid_priority_rejected(self):
        """
        Given priority not in ['low', 'medium', 'high'],
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        payload['priority'] = 'urgent'

        response, data = self.post_json(self.create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('priority', data)

    def test_invalid_status_rejected(self):
        """
        Given status not in ['pending', 'completed'],
        Then 400 Bad Request is returned.
        """
        payload = self.valid_payload.copy()
        payload['status'] = 'in_progress'

        response, data = self.post_json(self.create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', data)

    def test_completed_status_sets_completed_at(self):
        """
        Given status='completed' on creation,
        Then completed_at is automatically populated.
        """
        payload = self.valid_payload.copy()
        payload['status'] = 'completed'

        response, data = self.post_json(self.create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = self._get_first_task()
        self.assertIsNotNone(task.completed_at)

    def test_optional_fields_omitted(self):
        """
        Given only title and password (minimum required),
        Then task is created with sensible defaults.
        """
        payload = {'title': 'Minimal task'}

        response, data = self.post_json(self.create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = self._get_first_task()
        self.assertEqual(task.description, '')
        self.assertEqual(task.priority, 'medium')
        self.assertEqual(task.status, 'pending')
        self.assertIsNone(task.due_date)
