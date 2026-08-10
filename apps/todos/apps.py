from django.apps import AppConfig


class TodosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.todos'
    verbose_name = 'Todos'  # Optional: This sets a human-readable name for the app in the Django admin interface.
