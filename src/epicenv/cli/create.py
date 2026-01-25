"""Create command for generating .env files."""

from datetime import UTC, datetime
from pathlib import Path

import click

from .._config import find_pyproject_toml
from .._env import get_dot_env_file_str


def create_env_file(env_path: Path, overwrite: bool, backup: bool):
    """Create a .env file from pyproject.toml schema.

    Args:
        env_path: Path to the .env file to create
        overwrite: If True, overwrite without asking
        backup: If True and file exists, create backup before overwriting
    """
    # Find pyproject.toml
    pyproject_path = find_pyproject_toml()
    if not pyproject_path:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Could not find pyproject.toml. Make sure you're in a Python project directory."
        )
        raise click.Abort()

    click.echo(f"Using schema from: {click.style(str(pyproject_path), fg='cyan')}")

    # Make env_path absolute relative to current directory
    cwd = Path.cwd()
    if not env_path.is_absolute():
        env_path = cwd / env_path

    # Check if file exists and handle backup
    if env_path.exists():
        if not overwrite:
            if not click.confirm(f"File {env_path.relative_to(cwd)} already exists. Overwrite?"):
                click.echo("Aborted.")
                raise click.Abort()

        if backup:
            # Create backup with timestamp
            now = datetime.now(UTC)
            backup_path = env_path.with_name(f".env.{now.strftime('%Y%m%d%H%M%S')}")
            env_path.rename(backup_path)
            click.echo(
                click.style("Backup created: ", fg="yellow")
                + click.style(str(backup_path.relative_to(cwd)), fg="cyan")
            )

    # Generate .env file content
    try:
        dot_env_content = get_dot_env_file_str()
    except Exception as e:
        click.echo(click.style("Error generating .env file: ", fg="red", bold=True) + str(e))
        raise click.Abort()

    # Write the file
    env_path.write_text(dot_env_content)

    click.echo(
        click.style("Success! ", fg="green", bold=True)
        + f"Created {click.style(str(env_path.relative_to(cwd)), fg='cyan')}"
    )
