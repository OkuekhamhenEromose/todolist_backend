"""
URL configuration for the todos app.

Included under /api/v1/todos/ via config/urls.py
"""

from django.urls import path
from .views import TaskCreateView

urlpatterns = [
    path('', TaskCreateView.as_view(), name='task-create'),
]
