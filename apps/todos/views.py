"""
Views for the todos app.
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Task
from .serializers import TaskSerializer
# for filters.py
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TaskFilter
# for pagination.py
from .pagination import TaskPagination

# Create your views here.
class TaskListCreateView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating tasks.

    GET  /api/v1/todos/  → List tasks (paginated, filtered, searchable)
    POST /api/v1/todos/  → Create task

    Query parameters for GET:
        ?page=1&page_size=20          — Pagination
        ?status=pending               — Filter by status
        ?priority=high                — Filter by priority
        ?category=work                — Filter by category
        ?due_date_after=2026-08-01    — Filter due date range
        ?search=quarterly report      — Search title and description
        ?ordering=-due_date           — Sort by due date descending

    Authentication: Required
    """
    # Queryset required by the generic view for serializer context, was created earlier but not used
    # queryset = Task.objects.all()

    # The serializer handles validation and object creation
    serializer_class = TaskSerializer
    # Only authenticated users can create tasks
    permission_classes = [IsAuthenticated]

    pagination_class = TaskPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_class = TaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at', 'title']
    ordering = ['-created_at']  # Default ordering: newest first

    def get_queryset(self):
        """
        CRITICAL SECURITY METHOD.

        This is the authorization boundary. Instead of returning
        Task.objects.all() (which would leak every user's tasks),
        we scope the queryset to the authenticated user only.

        Every filter, search, and pagination operation is constrained
        to this user's tasks because it operates on this queryset.
        """
        user = self.request.user
        return Task.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        Hook into the creation process to inject the current user.

        Why override this instead of handling it in the serializer?
        - Separation of concerns: The serializer validates data.
          The view handles the HTTP request context (who is the user?).
        - Security: The serializer doesn't know about requests.
          The view does. This prevents the serializer from being
          tricked into using a user_id from untrusted input.
        """
        serializer.save(user=self.request.user)
