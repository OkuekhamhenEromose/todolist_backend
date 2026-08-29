"""
Task model for the todos app.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

# Create your models here.
class Task(models.Model):
    """
    Represents a single todo item in the database.

    Design decisions:
    - user: ForeignKey to AUTH_USER_MODEL. CASCADE delete ensures
      cleanup when a user is removed. related_name='tasks' allows
      user.tasks.all() to fetch all tasks for that user.
    - title: Limited to 200 chars to prevent UI breakage.
    - description: TEXT field for unlimited-length notes.
    - status: CharField with choices (database + ORM enforcement).
    - priority: CharField with choices.
    - category: Free-text label (VARCHAR 50). Not a foreign key yet (YAGNI).
    - due_date: DATE (not DateTime) because deadlines are day-level.
    - completed_at: Set automatically by save() when status='completed'.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Django best practice. Avoids circular imports and respects custom user models.
        on_delete=models.CASCADE, # Matches Phase 3 design. User deletion cleans up their tasks.
        related_name='tasks', # Enables user.tasks.all() — clean, readable reverse queries.
        db_index=True, # Every task query starts with WHERE user_id = X. Indexing is mandatory for performance.
        help_text="The owner of this task"
    )

    title = models.CharField(
        max_length=200,
        help_text="Brief description of the task"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Detailed notes, links, sub-tasks"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Current state of the task"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        db_index=True,
        help_text="Urgently level"
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        default='',
        db_index=True,
        help_text="Context label (e.g., work, personal)"
    )

    due_date = models.DateField( # Deadlines are day-level. Using DateTimeField would force clients to send time components they don't care about.
        null=True,
        blank=True,
        db_index=True,
        help_text="Deadline (optional)"
    )

    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at'] # Newest first, matching our API design
        indexes = [
            # Composite indexes for the most common query patterns
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'priority']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'due_date']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """
        Override save to auto-manage completed_at timestamp.

        Business rule: When a task is marked completed, record the exact
        moment of completion. When reverted to pending, clear the timestamp.
        """
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()

        elif self.status == 'pending' and self.completed_at:
            self.completed_at = None

        super().save(*args, **kwargs)
