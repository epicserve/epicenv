"""Django framework integration."""

import os

import click

from .base import FrameworkIntegration


class DjangoSuperuserIntegration(FrameworkIntegration):
    """Django superuser creation integration."""

    def is_available(self) -> tuple[bool, str | None]:
        """Check if Django is installed."""
        try:
            import django  # noqa: F401

            return True, None
        except ImportError:
            return False, "Django is not installed"

    def execute(self, **kwargs) -> bool:
        """Create Django superuser. Implementation in standalone functions below."""
        raise NotImplementedError("Use standalone functions for Django operations")


def detect_settings_module() -> str | None:
    """
    Auto-detect Django settings module.

    Priority:
    1. DJANGO_SETTINGS_MODULE env var
    2. pyproject.toml [tool.epicenv.django] settings_module
    3. Return None (let Django error handle it)

    Returns:
        Settings module string or None
    """
    # Check environment variable first
    if "DJANGO_SETTINGS_MODULE" in os.environ:
        return os.environ["DJANGO_SETTINGS_MODULE"]

    # Check pyproject.toml
    try:
        from .._config import find_pyproject_toml, get_config

        pyproject_path = find_pyproject_toml()
        if pyproject_path:
            config = get_config(pyproject_path)
            if config and "django" in config:
                settings_module = config["django"].get("settings_module")
                if settings_module:
                    return settings_module
    except Exception:  # noqa: S110
        # If config loading fails, continue with other detection methods
        pass

    return None


def setup_django(settings_module: str | None = None) -> None:
    """
    Initialize Django.

    Args:
        settings_module: Optional explicit settings module

    Raises:
        click.ClickException: If Django setup fails
    """
    import django
    from django.conf import settings

    # Set settings module if provided
    if settings_module:
        os.environ["DJANGO_SETTINGS_MODULE"] = settings_module
    else:
        # Try to auto-detect
        detected = detect_settings_module()
        if detected:
            os.environ["DJANGO_SETTINGS_MODULE"] = detected
        elif "DJANGO_SETTINGS_MODULE" not in os.environ:
            raise click.ClickException(
                "Django settings not configured.\n\n"
                "Set DJANGO_SETTINGS_MODULE environment variable or use --settings flag:\n"
                "  epicenv create-superuser --settings myapp.settings.local"
            )

    # Initialize Django
    if not settings.configured:
        try:
            django.setup()
        except Exception as e:
            raise click.ClickException(f"Failed to initialize Django: {e}") from e


def user_exists(username: str, database: str = "default") -> bool:
    """
    Check if user exists in database.

    Args:
        username: Username to check
        database: Database alias (default: "default")

    Returns:
        True if user exists, False otherwise
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.using(database).filter(username=username).exists()


def create_superuser(username: str, email: str, password: str, database: str = "default") -> bool:
    """
    Create a Django superuser.

    Args:
        username: Superuser username
        email: Superuser email
        password: Superuser password
        database: Database alias (default: "default")

    Returns:
        True if successful

    Raises:
        Exception: If user creation fails
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    User.objects.db_manager(database).create_superuser(username=username, email=email, password=password)
    return True


def update_superuser(username: str, email: str, password: str, database: str = "default") -> bool:
    """
    Update an existing superuser's password and email.

    Args:
        username: Superuser username
        email: New email
        password: New password
        database: Database alias (default: "default")

    Returns:
        True if successful

    Raises:
        Exception: If update fails
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.using(database).get(username=username)
    user.email = email
    user.set_password(password)
    user.save(using=database)
    return True
