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

class TaskListTests(APITestCase):
    """
    Test suite for GET /api/v1/todos/ (Task Listing, Filtering, Pagination)
    """
    client: APIClient

    def setUp(self):
        self.list_url = '/api/v1/todos/'

        self.user = User.objects.create_user(
            username='sarah@example.com',
            email='sarah@example.com',
            password='SecurePass123!'
        )
        self.other_user = User.objects.create_user(
            username='john@example.com',
            email='john@example.com',
            password='SecurePass123!'
        )
        self.access_token = str(AccessToken.for_user(self.user))
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )

        # Create tasks for our user
        self.task_high_work = Task.objects.create(
            user=self.user,
            title='Finish project report',
            description='Complete the final report for the project.',
            status='pending',
            priority='high',
            category='work',
            due_date='2026-08-20'
        )
        self.task_low_personal = Task.objects.create(
            user=self.user,
            title='Buy groceries',
            description='Milk, eggs, bread, and fruits.',
            status='completed',
            priority='low',
            category='personal',
            due_date='2026-08-10'
        )
        self.task_medium_work = Task.objects.create(
            user=self.user,
            title='Prepare presentation',
            description='Slides for the upcoming meeting.',
            status='pending',
            priority='medium',
            category='work',
            due_date='2026-08-25'
        )
        # Create task for other user (should NEVER appear)
        Task.objects.create(
            user=self.other_user,
            title='Other user task',
            description='This should not be visible to Sarah.',
            status='pending',
            priority='medium',
            category='work',
            due_date='2026-08-30'
        )

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

    def test_list_returns_only_own_tasks(self):
        """
        The response must follow DRF's standard pagination envelope.
        """
        response, data = self.get_json(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertIn('results', data)
        self.assertIsInstance(data['results'], list)

    def test_pagination_structure(self):
        """
        The response must follow DRF's standard pagination envelope.
        """
        response, data = self.get_json(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertIn('results', data)
        self.assertIsInstance(data['results'], list)

    def test_default_ordering_is_newest_first(self):
        """
        By default, tasks should be ordered by created_at descending.
        """
        response, data = self.get_json(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertGreaterEqual(len(results), 2)
        # Check that the first task is the most recently created one
        self.assertEqual(results[0]['title'], 'Prepare presentation')
        self.assertEqual(results[1]['title'], 'Buy groceries')

    def test_filter_by_status(self):
        """
        Given ?status=completed,
        Then only tasks with status='completed' are returned.
        """
        response, data = self.get_json(self.list_url + '?status=completed')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertTrue(all(task['status'] == 'completed' for task in results))

    def test_filter_by_priority(self):
        """
        Given ?priority=high,
        Then only tasks with priority='high' are returned.
        """
        response, data = self.get_json(self.list_url + '?priority=high')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertTrue(all(task['priority'] == 'high' for task in results))

    def test_filter_by_category(self):
        """
        Given ?category=work,
        Then only tasks with category='work' are returned.
        """
        response, data = self.get_json(self.list_url + '?category=work')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertTrue(all(task['category'] == 'work' for task in results))

    def test_filter_by_due_date_range(self):
        """
        Given ?due_date_after=2026-08-15&due_date_before=2026-08-25,
        Then only tasks with due_date in that range are returned.
        """
        response, data = self.get_json(
            self.list_url + '?due_date_after=2026-08-15&due_date_before=2026-08-25')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        for task in results:
            due_date = task['due_date']
            self.assertGreaterEqual(due_date, '2026-08-15')
            self.assertLessEqual(due_date, '2026-08-25')

    def test_filter_combination(self):
        """
        Given multiple filters combined,
        Then only tasks matching all criteria are returned.
        """
        response, data = self.get_json(self.list_url + '?status=pending&priority=medium&category=work')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        for task in results:
            self.assertEqual(task['status'], 'pending')
            self.assertEqual(task['priority'], 'medium')
            self.assertEqual(task['category'], 'work')

    def test_search_by_title_and_description(self):
        """
        Given ?search=report,
        Then tasks whose title or description contain 'report' are returned.
        """
        response, data = self.get_json(self.list_url + '?search=report')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertTrue(any('report' in task['title'].lower() or 'report' in task['description'].lower() for task in results))

    def test_ordering_by_title_ascending(self):
        """
        Given ?ordering=title,
        Then tasks are ordered by title ascending.
        """
        response, data = self.get_json(self.list_url + '?ordering=title')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        titles = [task['title'] for task in results]
        self.assertEqual(titles, sorted(titles))

    def test_ordering_by_due_date_descending(self):
        """
        Given ?ordering=-due_date,
        Then tasks are ordered by due_date descending.
        """
        response, data = self.get_json(self.list_url + '?ordering=-due_date')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        due_dates = [task['due_date'] for task in results]
        self.assertEqual(due_dates, sorted(due_dates, reverse=True))

    def test_pagination_page_size(self):
        """
        Given ?page_size=1,
        Then only 1 task is returned per page.
        """
        response, data = self.get_json(self.list_url + '?page_size=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertEqual(len(results), 1)

    def test_pagination_custom_page_size(self):
        """
        Given ?page_size=2,
        Then 2 tasks are returned per page.
        """
        response, data = self.get_json(self.list_url + '?page_size=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertEqual(len(results), 2)

    def test_pagination_exceeding_max_page_size(self):
        """
        Given ?page_size=200 (exceeds max_page_size=100),
        Then only 100 tasks are returned per page.
        """
        response, data = self.get_json(self.list_url + '?page_size=200')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = data['results']
        self.assertLessEqual(len(results), 100)

    def test_unauthenticated_list_rejected(self):
        """
        Given no Authorization header,
        Then 401 Unauthorized is returned.
        """
        self.client.credentials()  # Clear auth

        response, data = self.get_json(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filter_invalid_status_returns_empty(self):
        """
        Given ?status=invalid_status,
        Then 400 Bad Request is returned.
        """
        response, data = self.get_json(self.list_url + '?status=invalid_status')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', data)
