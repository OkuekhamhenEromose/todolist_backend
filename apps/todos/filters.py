"""
Filter configuration for Task model.
"""

import django_filters
from .models import Task

class TaskFilter(django_filters.FilterSet):
    """
    Enables URL-based filtering:
        ?status=pending
        ?priority=high
        ?category=work
        ?due_date_after=2026-08-01
        ?due_date_before=2026-08-31
    """
    due_date_after = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_date_before = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')

    class Meta:
        model = Task
        fields = ['status', 'priority', 'category']
