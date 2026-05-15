"""Main CLI entry point for epicenv."""

from pathlib import Path

import click

from .._exceptions import ConfigError


def _handle_config_error(e: ConfigError) -> None:
    """Surface ConfigError as a clean click message instead of a traceback."""
    click.echo(click.style("Error: ", fg="red", bold=True) + str(e), err=True)
    raise click.Abort() from e


@click.group()
@click.version_option(package_name="epicenv")
def cli():
    """
    Environment variable management tool for Python projects.

    Define your environment variables in pyproject.toml and use epicenv
    to create, validate, and manage .env files.
    """
    pass


@cli.command()
@click.option("--path", type=click.Path(), default=".env", help="Path to .env file to create")
@click.option("--overwrite", is_flag=True, help="Overwrite existing .env file without backup")
@click.option("--backup/--no-backup", default=True, help="Backup existing .env file (default: yes)")
@click.option(
    "--min",
    "minimal",
    is_flag=True,
    help="Minimal output: only required variables (no defaults), no help text or comments",
)
def create(path: str, overwrite: bool, backup: bool, minimal: bool):
    """
    Create a .env file from the project schema.

    Reads the schema from .env.toml, a file pointed to by
    [tool.epicenv] config_file, or [tool.epicenv.variables] in
    pyproject.toml and generates an initial .env file.
    """
    from .create import create_env_file

    try:
        create_env_file(Path(path), overwrite, backup, minimal=minimal)
    except ConfigError as e:
        _handle_config_error(e)


@cli.command()
@click.option("--path", type=click.Path(), default=".env", help="Path to .env file to compare")
def diff(path: str):
    """
    Show differences between .env file and schema.

    Compares your .env file with the project schema and reports:
    - Missing required variables
    - Missing optional variables (with defaults)
    - Orphaned variables not in schema
    """
    from .diff import diff_env_file

    try:
        diff_env_file(Path(path))
    except ConfigError as e:
        _handle_config_error(e)


@cli.command()
@click.option("--strict", is_flag=True, help="Exit with error code if validation fails")
def validate(strict: bool):
    """
    Validate current environment against schema.

    Checks that all required variables from the project schema are set in the
    current environment.
    """
    from .validate import validate_env

    try:
        validate_env(strict)
    except ConfigError as e:
        _handle_config_error(e)


@cli.group()
def secrets():
    """
    Manage secrets from 1Password and other providers.

    Retrieve secrets at runtime for use in automation and deployment workflows.
    """
    pass


@secrets.command()
@click.argument("reference")
@click.option("--fields", help="Comma-separated list of fields to retrieve")
@click.option(
    "--format",
    type=click.Choice(["json", "env", "plain"]),
    default="json",
    help="Output format (default: json)",
)
@click.option("--silent", is_flag=True, help="Suppress warnings")
def get(reference: str, fields: str | None, format: str, silent: bool):
    r"""
    Retrieve secrets from 1Password.

    REFERENCE is the 1Password secret reference:
    - Full path: op://vault/item/field
    - Item with fields: op://vault/item (use with --fields)

    Examples:
      # Get single field (plain text output)
      epicenv secrets get op://Production/Database/password

      # Get multiple fields as JSON
      epicenv secrets get op://Production/Admin --fields username,email,password

      # Get fields as environment variables
      epicenv secrets get op://Production/Admin --fields username,email --format env

      # Pipe to create-superuser
      epicenv secrets get op://vault/admin --fields username,email,password | \
        epicenv create-superuser
    """
    from .secrets import get_secrets

    get_secrets(reference, fields, format, silent)


@cli.command("create-superuser")
@click.option("--username", help="Superuser username")
@click.option("--email", help="Superuser email")
@click.option(
    "--password",
    help=(
        "Superuser password (NOT recommended for production — "
        "appears in shell history; prefer piped stdin or env vars)"
    ),
)
@click.option("--settings", help="Django settings module (e.g., myapp.settings.local)")
@click.option("--database", default="default", help="Database alias (default: default)")
@click.option("--force", is_flag=True, help="Update existing user instead of skipping")
def create_superuser(
    username: str | None,
    email: str | None,
    password: str | None,
    settings: str | None,
    database: str,
    force: bool,
):
    r"""
    Create Django superuser idempotently.

    Automatically detects credentials from multiple sources (in priority order):
    1. Explicit flags (--username, --email, --password)
    2. Stdin (piped JSON data)
    3. Environment variables (DJANGO_SUPERUSER_*)

    Examples:
      # From 1Password (recommended - most secure)
      epicenv secrets get op://vault/admin --fields username,email,password | \
        epicenv create-superuser

      # From environment variables (auto-detected)
      export DJANGO_SUPERUSER_USERNAME=admin
      export DJANGO_SUPERUSER_EMAIL=admin@example.com
      export DJANGO_SUPERUSER_PASSWORD=secret
      epicenv create-superuser

      # From explicit flags (for testing/automation)
      epicenv create-superuser --username admin --email admin@example.com --password secret

      # With custom settings module
      epicenv create-superuser --settings myapp.settings.production

      # Update existing user password
      epicenv create-superuser --username admin --password newpass --force
    """
    from .create_superuser import create_django_superuser

    create_django_superuser(username, email, password, settings, database, force)


if __name__ == "__main__":
    cli()
