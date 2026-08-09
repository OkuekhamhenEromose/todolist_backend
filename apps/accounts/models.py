
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
# Why must this happen before the first migration?
# If you run migrate with Django's default user model, Django creates the auth_user table. Once that table exists, Django refuses to switch AUTH_USER_MODEL to a custom model because it would orphan existing user data. You'd need to dump data, delete migrations, recreate the database, and reload data. Starting custom avoids this entirely
class User(AbstractUser):
    """
    Custom User model that extends Django's AbstractUser.
    This allows for future customization of the User model if needed.
    """
    email = models.EmailField(unique=True)  # Ensure email is unique for each user

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'

    def __str__(self):
        return self.email  # Return the email as the string representation of the User