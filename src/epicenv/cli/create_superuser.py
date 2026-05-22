"""Create superuser CLI command implementation."""

import json
import os
import select
import sys

import click

from ..frameworks.django import DjangoSuperuserIntegration, setup_django


def _stdin_has_data() -> bool:
    """
    Return True when stdin is non-interactive AND has buffered data ready to read.

    Returns False for interactive terminals or when select() can't inspect the stream
    (e.g. on Windows or when stdin has been replaced by a non-fd stream); the caller
    then continues to other input sources rather than blocking on a `json.load`.
    """
    if sys.stdin.isatty():
        return False
    try:
        return bool(select.select([sys.stdin], [], [], 0.0)[0])
    except (OSError, ValueError):
        return False


def create_django_superuser(
    username: str | None,
    email: str | None,
    password: str | None,
    settings: str | None,
    database: str,
    force: bool,
):
    """
    Create Django superuser with auto-detection of input source.

    Input priority:
    1. Explicit flags (--username, --email, --password)
    2. Stdin (if not a TTY, reads JSON)
    3. Environment variables (DJANGO_SUPERUSER_*)
    4. Error if none of the above

    Args:
        username: Username from command-line flag
        email: Email from command-line flag
        password: Password from command-line flag
        settings: Django settings module
        database: Database alias
        force: Whether to update existing user
    """
    # Detect input source in priority order:
    # 1. Explicit flags
    # 2. Piped JSON on stdin
    # 3. Environment variables
    # 4. Error
    have_credentials = bool(username and email and password)

    if not have_credentials and _stdin_has_data():
        try:
            data = json.load(sys.stdin)
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
        except json.JSONDecodeError as e:
            click.echo(click.style("Error: ", fg="red", bold=True) + f"Invalid JSON from stdin: {e}", err=True)
            click.echo("\nExpected JSON format:", err=True)
            click.echo('  {"username": "admin", "email": "admin@example.com", "password": "secret"}', err=True)
            sys.exit(1)

        if not all([username, email, password]):
            missing = [
                name for name, value in (("username", username), ("email", email), ("password", password))
                if not value
            ]
            click.echo(click.style("Error: ", fg="red", bold=True) + "Missing required fields in JSON", err=True)
            click.echo(f"Required: {', '.join(missing)}", err=True)
            click.echo("\nExample JSON format:", err=True)
            click.echo('  {"username": "admin", "email": "admin@example.com", "password": "secret"}', err=True)
            sys.exit(1)
        have_credentials = True

    if not have_credentials and os.getenv("DJANGO_SUPERUSER_USERNAME"):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            missing = [
                name for name, value in (
                    ("DJANGO_SUPERUSER_USERNAME", username),
                    ("DJANGO_SUPERUSER_EMAIL", email),
                    ("DJANGO_SUPERUSER_PASSWORD", password),
                )
                if not value
            ]
            click.echo(click.style("Error: ", fg="red", bold=True) + "Missing environment variables", err=True)
            click.echo(f"Required: {', '.join(missing)}", err=True)
            sys.exit(1)
        have_credentials = True

    if not have_credentials:
        click.echo(click.style("Error: ", fg="red", bold=True) + "No credentials provided", err=True)
        click.echo("\nProvide credentials via one of these methods:", err=True)
        click.echo("  1. Explicit flags:", err=True)
        click.echo(
            "       epicenv create-superuser --username admin --email admin@example.com --password secret", err=True
        )
        click.echo("  2. Pipe JSON:", err=True)
        click.echo(
            '       echo \'{"username":"admin","email":"admin@example.com","password":"secret"}\' | '
            "epicenv create-superuser",
            err=True,
        )
        click.echo("  3. Environment variables:", err=True)
        click.echo("       export DJANGO_SUPERUSER_USERNAME=admin", err=True)
        click.echo("       export DJANGO_SUPERUSER_EMAIL=admin@example.com", err=True)
        click.echo("       export DJANGO_SUPERUSER_PASSWORD=secret", err=True)
        click.echo("       epicenv create-superuser", err=True)
        sys.exit(1)

    # Check Django availability
    integration = DjangoSuperuserIntegration()
    available, error = integration.is_available()
    if not available:
        click.echo(click.style("Error: ", fg="red", bold=True) + error, err=True)
        click.echo("\nInstall Django:", err=True)
        click.echo("  pip install django", err=True)
        click.echo("  # or", err=True)
        click.echo("  uv add django", err=True)
        sys.exit(1)

    # Setup Django
    try:
        setup_django(settings)
    except click.ClickException:
        # Re-raise click exceptions (they have proper formatting)
        raise
    except Exception as e:
        click.echo(click.style("Error: ", fg="red", bold=True) + f"Django setup failed: {e}", err=True)
        sys.exit(1)

    # Create or update the superuser
    try:
        result = integration.execute(
            username=username,
            email=email,
            password=password,
            database=database,
            force=force,
        )
    except Exception as e:
        click.echo(click.style("Error: ", fg="red", bold=True) + f"Database error: {e}", err=True)
        sys.exit(1)

    if result == "exists":
        click.echo(click.style("✓ ", fg="green", bold=True) + f"Superuser '{username}' already exists")
        click.echo("\nUse --force to update the existing user's password", err=True)
    elif result == "updated":
        click.echo(click.style("✓ ", fg="green", bold=True) + f"Superuser '{username}' updated successfully")
    elif result == "created":
        click.echo(click.style("✓ ", fg="green", bold=True) + f"Superuser '{username}' created successfully")
