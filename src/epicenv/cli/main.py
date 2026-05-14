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
def create(path: str, overwrite: bool, backup: bool):
    """
    Create a .env file from the project schema.

    Reads the schema from .env.toml, a file pointed to by
    [tool.epicenv] config_file, or [tool.epicenv.variables] in
    pyproject.toml and generates an initial .env file.
    """
    from .create import create_env_file

    try:
        create_env_file(Path(path), overwrite, backup)
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


if __name__ == "__main__":
    cli()
