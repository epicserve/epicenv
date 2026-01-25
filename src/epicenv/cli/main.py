"""Main CLI entry point for epicenv."""

from pathlib import Path

import click


@click.group()
@click.version_option(package_name="epicenv")
def cli():
    """Environment variable management tool for Python projects.

    Define your environment variables in pyproject.toml and use epicenv
    to create, validate, and manage .env files.
    """
    pass


@cli.command()
@click.option("--path", type=click.Path(), default=".env", help="Path to .env file to create")
@click.option("--overwrite", is_flag=True, help="Overwrite existing .env file without backup")
@click.option("--backup/--no-backup", default=True, help="Backup existing .env file (default: yes)")
def create(path: str, overwrite: bool, backup: bool):
    """Create a .env file from pyproject.toml schema.

    Reads the [tool.epicenv.variables] section from pyproject.toml
    and generates an initial .env file with help text, types, and defaults.
    """
    from .create import create_env_file

    create_env_file(Path(path), overwrite, backup)


@cli.command()
@click.option("--path", type=click.Path(), default=".env", help="Path to .env file to compare")
def diff(path: str):
    """Show differences between .env file and schema.

    Compares your .env file with the schema defined in pyproject.toml
    and reports:
    - Missing required variables
    - Missing optional variables (with defaults)
    - Orphaned variables not in schema
    """
    from .diff import diff_env_file

    diff_env_file(Path(path))


@cli.command()
@click.option("--strict", is_flag=True, help="Exit with error code if validation fails")
def validate(strict: bool):
    """Validate current environment against schema.

    Checks that all required variables from pyproject.toml schema
    are set in the current environment.
    """
    from .validate import validate_env

    validate_env(strict)


if __name__ == "__main__":
    cli()
