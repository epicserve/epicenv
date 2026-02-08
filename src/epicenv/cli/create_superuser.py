"""Create superuser CLI command implementation."""

import json
import os
import sys

import click

from ..frameworks.django import (
    DjangoSuperuserIntegration,
    create_superuser,
    setup_django,
    update_superuser,
    user_exists,
)


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
    # Auto-detect input source (priority order)

    # 1. Explicit flags
    if username and email and password:
        # All explicit flags provided, use them
        pass

    # 2. Stdin (check if not a TTY and has data)
    elif not sys.stdin.isatty():
        # Check if there's actually data on stdin
        import select

        # Use select to check if stdin has data (non-blocking)
        # This prevents hanging when stdin is not a TTY but has no data
        if select.select([sys.stdin], [], [], 0.0)[0]:
            try:
                data = json.load(sys.stdin)
                username = data.get("username")
                email = data.get("email")
                password = data.get("password")

                if not all([username, email, password]):
                    missing = []
                    if not username:
                        missing.append("username")
                    if not email:
                        missing.append("email")
                    if not password:
                        missing.append("password")

                    click.echo(
                        click.style("Error: ", fg="red", bold=True) + "Missing required fields in JSON", err=True
                    )
                    click.echo(f"Required: {', '.join(missing)}", err=True)
                    click.echo("\nExample JSON format:", err=True)
                    click.echo('  {"username": "admin", "email": "admin@example.com", "password": "secret"}', err=True)
                    sys.exit(1)

            except json.JSONDecodeError as e:
                click.echo(click.style("Error: ", fg="red", bold=True) + f"Invalid JSON from stdin: {e}", err=True)
                click.echo("\nExpected JSON format:", err=True)
                click.echo('  {"username": "admin", "email": "admin@example.com", "password": "secret"}', err=True)
                sys.exit(1)
            except KeyError as e:
                click.echo(click.style("Error: ", fg="red", bold=True) + f"Missing key in JSON: {e}", err=True)
                sys.exit(1)
        else:
            # stdin is not a TTY but has no data - fall through to env vars
            pass

    # 3. Environment variables
    elif os.getenv("DJANGO_SUPERUSER_USERNAME"):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            missing = []
            if not username:
                missing.append("DJANGO_SUPERUSER_USERNAME")
            if not email:
                missing.append("DJANGO_SUPERUSER_EMAIL")
            if not password:
                missing.append("DJANGO_SUPERUSER_PASSWORD")

            click.echo(click.style("Error: ", fg="red", bold=True) + "Missing environment variables", err=True)
            click.echo(f"Required: {', '.join(missing)}", err=True)
            sys.exit(1)

    # 4. No valid input
    else:
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

    # Check if user exists
    try:
        exists = user_exists(username, database)
    except Exception as e:
        click.echo(click.style("Error: ", fg="red", bold=True) + f"Database error: {e}", err=True)
        sys.exit(1)

    if exists:
        if not force:
            click.echo(click.style("✓ ", fg="green", bold=True) + f"Superuser '{username}' already exists")
            click.echo("\nUse --force to update the existing user's password", err=True)
            sys.exit(0)
        else:
            # Update existing user
            try:
                update_superuser(username, email, password, database)
                click.echo(click.style("✓ ", fg="green", bold=True) + f"Superuser '{username}' updated successfully")
            except Exception as e:
                click.echo(click.style("Error: ", fg="red", bold=True) + f"Failed to update superuser: {e}", err=True)
                sys.exit(1)
    else:
        # Create new user
        try:
            create_superuser(username, email, password, database)
            click.echo(click.style("✓ ", fg="green", bold=True) + f"Superuser '{username}' created successfully")
        except Exception as e:
            click.echo(click.style("Error: ", fg="red", bold=True) + f"Failed to create superuser: {e}", err=True)
            sys.exit(1)
