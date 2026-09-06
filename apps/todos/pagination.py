"""
Custom pagination configuration for the todos app.
"""

from rest_framework.pagination import PageNumberPagination

class TaskPagination(PageNumberPagination):
    """
    Paginates task lists to prevent unbounded result sets.

    Query parameters:
        ?page=2          — Navigate to page 2
        ?page_size=50    — Request 50 items per page (max 100)

    Why custom class instead of global settings?
    - Different resources might need different page sizes
    - Task lists are the primary view, so we allow flexible sizing
    - Keeps configuration close to the resource it affects
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
