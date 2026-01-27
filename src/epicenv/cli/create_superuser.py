"""Create superuser command for Django projects using 1Password credentials."""

from __future__ import annotations

from typing import NamedTuple

import click

from .._config import find_pyproject_toml, get_django_config
from ..initializers._onepassword import _check_onepassword_available, _fetch_from_onepassword


class SuperuserCredentials(NamedTuple):
    """Container for superuser credentials."""

    username: str
    email: str
    password: str


def _fetch_superuser_credentials(
    reference: str,
    config: dict,
) -> tuple[SuperuserCredentials | None, str | None]:
    """
    Fetch superuser credentials from 1Password.

    Args:
        reference: Base 1Password reference (e.g., "op://vault/item")
        config: Django config dict with optional field name mappings

    Returns:
        Tuple of (credentials, error_message)
    """
    # Get field name mappings (or use defaults)
    field_config = config.get("superuser_fields", {})
    username_field = field_config.get("username", "username")
    email_field = field_config.get("email", "email")
    password_field = field_config.get("password", "password")

    # Fetch each field
    username, error = _fetch_from_onepassword(f"{reference}/{username_field}")
    if error:
        return None, f"Failed to fetch username: {error}"

    email, error = _fetch_from_onepassword(f"{reference}/{email_field}")
    if error:
        return None, f"Failed to fetch email: {error}"

    password, error = _fetch_from_onepassword(f"{reference}/{password_field}")
    if error:
        return None, f"Failed to fetch password: {error}"

    return SuperuserCredentials(username=username, email=email, password=password), None


def _create_or_update_superuser(
    credentials: SuperuserCredentials,
    lookup_fields: list[str],
) -> tuple[bool, str, bool]:
    """
    Create or update a Django superuser.

    Args:
        credentials: The superuser credentials
        lookup_fields: Fields to use for existence check (e.g., ["username", "email"])

    Returns:
        Tuple of (success, message, was_created)
    """
    from .._django import (
        create_superuser,
        find_existing_user,
        update_user_password,
    )

    # Build lookup dict from credentials
    lookup_dict = {}
    if "username" in lookup_fields:
        lookup_dict["username"] = credentials.username
    if "email" in lookup_fields:
        lookup_dict["email"] = credentials.email

    # Check if user exists
    existing_user = find_existing_user(lookup_dict)

    if existing_user:
        # Update password for existing user
        success, error = update_user_password(existing_user, credentials.password)
        if success:
            return True, f"Updated password for existing user: {existing_user.username}", False
        return False, error or "Failed to update password", False

    # Create new superuser
    user, error = create_superuser(
        username=credentials.username,
        email=credentials.email,
        password=credentials.password,
    )

    if user:
        return True, f"Created superuser: {user.username}", True
    return False, error or "Failed to create superuser", False


def create_superuser(
    reference: str | None = None,
    settings_module: str | None = None,
) -> None:
    """
    Create a Django superuser from 1Password credentials.

    Args:
        reference: Optional 1Password reference override
        settings_module: Optional Django settings module
    """
    # 1. Find pyproject.toml
    pyproject_path = find_pyproject_toml()

    # 2. Load config (even if no pyproject.toml, we can use CLI args)
    config: dict = {}
    if pyproject_path:
        config = get_django_config(pyproject_path)

    # 3. Resolve reference
    final_reference = reference or config.get("superuser_reference")
    if not final_reference:
        click.echo(click.style("Error: ", fg="red", bold=True) + "No 1Password reference provided")
        click.echo("\nProvide via --reference flag or configure in pyproject.toml:")
        click.echo("[tool.epicenv.django]")
        click.echo('superuser_reference = "op://vault/item"')
        raise click.Abort()

    # 4. Check Django availability
    from .._django import check_django_available

    is_available, error = check_django_available()
    if not is_available:
        click.echo(click.style("Error: ", fg="red", bold=True) + (error or "Django not available"))
        click.echo("\nInstall Django with: pip install django")
        raise click.Abort()

    # 5. Setup Django environment
    from .._django import setup_django_environment

    success, error = setup_django_environment(settings_module)
    if not success:
        click.echo(click.style("Error: ", fg="red", bold=True) + (error or "Django setup failed"))
        raise click.Abort()

    # 6. Check database connectivity
    from .._django import check_database_ready

    success, error = check_database_ready()
    if not success:
        click.echo(click.style("Error: ", fg="red", bold=True) + (error or "Database not ready"))
        click.echo("\nMake sure your database is running.")
        raise click.Abort()

    # 7. Check user table exists
    from .._django import check_user_table_exists

    success, error = check_user_table_exists()
    if not success:
        click.echo(click.style("Error: ", fg="red", bold=True) + (error or "User table not found"))
        raise click.Abort()

    # 8. Check 1Password availability
    is_available, error = _check_onepassword_available()
    if not is_available:
        click.echo(click.style("Error: ", fg="red", bold=True) + "1Password CLI is not available")
        if error:
            click.echo(f"Reason: {error}")
        click.echo("\nSetup: https://developer.1password.com/docs/cli/get-started/")
        raise click.Abort()

    # 9. Fetch credentials
    click.echo(f"Fetching credentials from 1Password: {final_reference}")
    credentials, error = _fetch_superuser_credentials(final_reference, config)
    if not credentials:
        click.echo(click.style("Error: ", fg="red", bold=True) + (error or "Failed to fetch credentials"))
        raise click.Abort()

    # 10. Create or update user
    lookup_fields = config.get("superuser_lookup_fields", ["username"])
    success, message, was_created = _create_or_update_superuser(credentials, lookup_fields)

    if success:
        action = "Created" if was_created else "Updated"
        click.echo(click.style("Success! ", fg="green", bold=True) + f"{action} superuser: {credentials.username}")
    else:
        click.echo(click.style("Error: ", fg="red", bold=True) + message)
        raise click.Abort()
