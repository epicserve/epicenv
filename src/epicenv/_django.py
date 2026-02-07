"""
Django integration helpers.

This module provides helper functions for Django integration while keeping
Django as an optional dependency. Functions here handle Django setup,
database checks, and user model operations.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


def check_django_available() -> tuple[bool, str | None]:
    """
    Check if Django is importable.

    Returns:
        Tuple of (is_available, error_message)
    """
    try:
        import django  # noqa: F401

        return True, None
    except ImportError:
        return False, "Django is not installed"


def setup_django_environment(settings_module: str | None = None) -> tuple[bool, str | None]:
    """
    Set up Django if DJANGO_SETTINGS_MODULE is set.

    Args:
        settings_module: Optional Django settings module to use.
                        If not provided, uses DJANGO_SETTINGS_MODULE env var.

    Returns:
        Tuple of (success, error_message)
    """
    if settings_module:
        os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

    if "DJANGO_SETTINGS_MODULE" not in os.environ:
        return False, (
            "DJANGO_SETTINGS_MODULE environment variable is not set.\n"
            "Set it with: export DJANGO_SETTINGS_MODULE=myproject.settings\n"
            "Or use the --settings flag."
        )

    try:
        import django

        django.setup()
        return True, None
    except Exception as e:
        return False, f"Failed to setup Django: {e}"


def check_database_ready() -> tuple[bool, str | None]:
    """
    Check if Django database is configured and accessible.

    Returns:
        Tuple of (success, error_message)
    """
    try:
        from django.db import connection

        connection.ensure_connection()
        return True, None
    except Exception as e:
        return False, f"Database connection failed: {e}"


def check_user_table_exists() -> tuple[bool, str | None]:
    """
    Check if the user table exists in the database.

    Returns:
        Tuple of (exists, error_message)
    """
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        # Try to access the table
        User.objects.exists()
        return True, None
    except Exception as e:
        error_str = str(e).lower()
        if "no such table" in error_str or "does not exist" in error_str:
            return False, "User table does not exist. Run migrations first:\npython manage.py migrate"
        return False, f"Error checking user table: {e}"


def get_user_model_class() -> type[AbstractUser]:
    """
    Get the configured Django user model.

    Returns:
        The user model class (handles custom user models)
    """
    from django.contrib.auth import get_user_model

    return get_user_model()


def find_existing_user(lookup_fields: dict[str, str]) -> AbstractUser | None:
    """
    Check if a user exists matching any of the given fields.

    Uses OR logic - returns the first user matching any of the specified fields.

    Args:
        lookup_fields: Dict of field_name -> value to match

    Returns:
        User instance if found, None otherwise
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    User = get_user_model()

    if not lookup_fields:
        return None

    # Build OR query for all lookup fields
    query = Q()
    for field, value in lookup_fields.items():
        if value:
            query |= Q(**{field: value})

    if not query:
        return None

    return User.objects.filter(query).first()


def create_superuser(username: str, email: str, password: str) -> tuple[Any, str | None]:
    """
    Create a new Django superuser.

    Args:
        username: The username for the superuser
        email: The email for the superuser
        password: The password for the superuser

    Returns:
        Tuple of (user_instance, error_message)
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        return user, None
    except Exception as e:
        return None, f"Failed to create superuser: {e}"


def update_user_password(user: AbstractUser, password: str) -> tuple[bool, str | None]:
    """
    Update an existing user's password.

    Args:
        user: The user instance to update
        password: The new password

    Returns:
        Tuple of (success, error_message)
    """
    try:
        user.set_password(password)
        user.save(update_fields=["password"])
        return True, None
    except Exception as e:
        return False, f"Failed to update password: {e}"
