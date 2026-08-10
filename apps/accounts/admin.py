from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin

# Register your models here.
# The Django admin is a built-in superpower. It gives you a full CRUD interface for your database at /admin/. We'll use it to verify our User model works before building the API.
admin.site.register(User, UserAdmin)
