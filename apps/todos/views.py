"""
Views for the todos app.
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Task
from .serializers import TaskSerializer

# Create your views here.
class TaskCreateView(generics.CreateAPIView):
    """
    API endpoint for creating a new task.

    POST /api/v1/todos/

    Authentication: Required (Bearer token)
    Permission: IsAuthenticated
    """
    # Queryset required by the generic view for serializer context
    queryset = Task.objects.all()

    # The serializer handles validation and object creation
    serializer_class = TaskSerializer
    # Only authenticated users can create tasks
    permission_classes = [IsAuthenticated]

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
