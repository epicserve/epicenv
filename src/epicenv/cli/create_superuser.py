"""Create superuser command for Django projects using 1Password credentials."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import NamedTuple

import click

from .._config import find_pyproject_toml, get_django_config
from ..initializers._onepassword import _check_onepassword_available, _fetch_from_onepassword


class UserCredentials(NamedTuple):
    """User credentials for superuser creation."""

    username: str
    email: str
    password: str


def _fetch_superuser_credentials(
    reference: str,
    config: dict,
) -> tuple[UserCredentials | None, str | None]:
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

    return UserCredentials(username=username, email=email, password=password), None


# Inline script that will be executed via subprocess
_CREATE_SUPERUSER_SCRIPT = """
import sys
import os

# Parse arguments
username = sys.argv[1]
email = sys.argv[2]
password = sys.argv[3]
lookup_fields = sys.argv[4].split(',') if sys.argv[4] else ['username']

# Setup Django
import django
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

# Build lookup query
lookup_dict = {}
if 'username' in lookup_fields:
    lookup_dict['username'] = username
if 'email' in lookup_fields:
    lookup_dict['email'] = email

# Check if user exists
existing_user = None
if lookup_dict:
    query = Q()
    for field, value in lookup_dict.items():
        if value:
            query |= Q(**{field: value})
    if query:
        existing_user = User.objects.filter(query).first()

# Create or update
if existing_user:
    existing_user.set_password(password)
    existing_user.save(update_fields=['password'])
    print(f"UPDATED:{existing_user.username}")
else:
    user = User.objects.create_superuser(username=username, email=email, password=password)
    print(f"CREATED:{user.username}")
"""


def create_superuser(
    reference: str | None = None,
    settings_module: str | None = None,
) -> None:
    """
    Create a Django superuser from 1Password credentials.

    This command fetches credentials from 1Password on the host machine,
    then uses subprocess to create the superuser in Django's environment.

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

    # 4. Check 1Password availability (on host)
    is_available, error = _check_onepassword_available()
    if not is_available:
        click.echo(click.style("Error: ", fg="red", bold=True) + "1Password CLI is not available")
        if error:
            click.echo(f"Reason: {error}")
        click.echo("\nSetup: https://developer.1password.com/docs/cli/get-started/")
        raise click.Abort()

    # 5. Fetch credentials (on host)
    click.echo(f"Fetching credentials from 1Password: {final_reference}")
    credentials, error = _fetch_superuser_credentials(final_reference, config)
    if not credentials:
        click.echo(click.style("Error: ", fg="red", bold=True) + (error or "Failed to fetch credentials"))
        raise click.Abort()

    # 6. Prepare subprocess environment (inherit current env)
    subprocess_env = dict(os.environ)

    # 7. Set Django settings module if provided
    if settings_module:
        subprocess_env["DJANGO_SETTINGS_MODULE"] = settings_module

    # 8. Check if DJANGO_SETTINGS_MODULE is set
    if "DJANGO_SETTINGS_MODULE" not in subprocess_env:
        click.echo(click.style("Error: ", fg="red", bold=True) + "DJANGO_SETTINGS_MODULE not set")
        click.echo("\nSet it with: export DJANGO_SETTINGS_MODULE=myproject.settings")
        click.echo("Or use the --settings flag.")
        raise click.Abort()

    # 9. Execute subprocess to create/update superuser
    lookup_fields = config.get("superuser_lookup_fields", ["username"])
    lookup_str = ",".join(lookup_fields)

    try:
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                _CREATE_SUPERUSER_SCRIPT,
                credentials.username,
                credentials.email,
                credentials.password,
                lookup_str,
            ],
            env=subprocess_env,
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output to determine if user was created or updated
        output = result.stdout.strip()
        if output.startswith("CREATED:"):
            username = output.split(":", 1)[1]
            click.echo(click.style("Success! ", fg="green", bold=True) + f"Created superuser: {username}")
        elif output.startswith("UPDATED:"):
            username = output.split(":", 1)[1]
            click.echo(
                click.style("Success! ", fg="green", bold=True) + f"Updated password for existing user: {username}"
            )
        else:
            click.echo(
                click.style("Success! ", fg="green", bold=True)
                + f"Superuser operation completed: {credentials.username}"
            )

    except subprocess.CalledProcessError as e:
        click.echo(click.style("Error: ", fg="red", bold=True) + "Failed to create/update superuser")
        if e.stderr:
            click.echo(f"\n{e.stderr}")
        raise click.Abort() from e
    except Exception as e:
        click.echo(click.style("Error: ", fg="red", bold=True) + f"Subprocess execution failed: {e}")
        raise click.Abort() from e


@click.command("create-superuser")
@click.option(
    "--reference",
    help="1Password reference to superuser credentials (e.g., op://vault/item)",
)
@click.option(
    "--settings",
    "settings_module",
    help="Django settings module (e.g., 'myproject.settings')",
)
def cli(reference: str | None, settings_module: str | None) -> None:
    """Create or update Django superuser from 1Password credentials."""
    create_superuser(reference=reference, settings_module=settings_module)
