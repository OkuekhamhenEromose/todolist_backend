"""
Serializers for the todos app.
"""

from dataclasses import fields
from pyexpat import model
from random import choice

from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for Task model.

    Handles:
    - Validation of status/priority against model choices
    - Prevention of empty/whitespace-only titles
    - Auto-assignment of user from request context (view layer)
    - Read-only user field (security: client cannot specify owner)
    """

    # user is included so the frontend knows who owns the task,
    # but it is read-only. The view injects request.user on creation
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id',
            'user',
            'title',
            'description',
            'status',
            'priority',
            'category',
            'due_date',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'updated_at',
            'compltetd_at',
        ]

    def validated_title(self, value):
        """
        Field-level validator for title.

        CharField with required=True prevents empty strings,
        but doesn't catch strings of only whitespace.
        This validator ensures "   " is rejected.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty")
        return value.strip()

    def validated_status(self, value):
        """
        Ensure status is a valid choice.
        Model choices enforce this at the DB level, but we validate
        at the API layer to return a clean 400 error before hitting the DB.
        """
        valid_statuses = [
            choice[0] for choice in Task.STATUS_CHOICES
        ]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {','.join(valid_statuses)}.")
        return value

    def validated_priority(self, value):
        """Same pattern as validate_status."""
        valid_priorities = [choice[0] for choice in Task.PRIORITY_CHOICES]
        if value not in valid_priorities:
            raise serializers.ValidationError(f"Priority must be one of: {','.join(valid_priorities)}.")
        return value
