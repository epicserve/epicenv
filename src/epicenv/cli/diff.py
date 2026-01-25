"""Diff command for comparing .env files with schema."""

import re
from pathlib import Path

import click

from .._config import find_pyproject_toml, load_schema


def diff_env_file(env_path: Path):
    """Compare .env file with pyproject.toml schema.

    Args:
        env_path: Path to the .env file to compare
    """
    # Find pyproject.toml
    pyproject_path = find_pyproject_toml()
    if not pyproject_path:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Could not find pyproject.toml. Make sure you're in a Python project directory."
        )
        raise click.Abort()

    # Load schema
    schema = load_schema(pyproject_path)
    if not schema:
        click.echo(
            click.style("Warning: ", fg="yellow", bold=True)
            + "No [tool.epicenv.variables] section found in pyproject.toml"
        )
        return

    click.echo(f"Using schema from: {click.style(str(pyproject_path), fg='cyan')}\n")

    # Make env_path absolute
    cwd = Path.cwd()
    if not env_path.is_absolute():
        env_path = cwd / env_path

    # Check if .env file exists
    if not env_path.exists():
        click.echo(click.style("Error: ", fg="red", bold=True) + f"{env_path.relative_to(cwd)} does not exist.")
        click.echo(f"\nRun {click.style('epicenv create', fg='green')} to create it.")
        raise click.Abort()

    # Read .env file and extract variable names
    with env_path.open() as f:
        env_lines = f.readlines()

    existing_vars = []
    for line in env_lines:
        # Match lines like: VAR=value or # VAR=value
        if re.match(r"^(#\s)?[_A-Z]+=.*", line):
            key, _value = line.split("=", 1)
            existing_vars.append(key.strip())

    # Check for missing variables
    missing_vars = []
    missing_default_vars = []

    for var_name, var_def in schema.items():
        has_default = var_def.get("default") is not None
        is_required = var_def.get("required", not has_default)

        # Check if variable exists (either uncommented or commented)
        var_exists = var_name in existing_vars or f"# {var_name}" in existing_vars

        if not var_exists:
            if is_required and not has_default:
                missing_vars.append(var_name)
            elif has_default:
                missing_default_vars.append(var_name)

    # Report missing variables
    issues_found = False

    if missing_vars:
        issues_found = True
        click.echo(click.style("Missing required variables:", fg="red", bold=True))
        for var in missing_vars:
            var_def = schema[var]
            help_text = var_def.get("help_text", "")
            click.echo(f"  • {click.style(var, fg='yellow')} - {help_text}")
        click.echo()

    if missing_default_vars:
        issues_found = True
        click.echo(click.style("Missing optional variables (have defaults):", fg="yellow", bold=True))
        for var in missing_default_vars:
            var_def = schema[var]
            default = var_def.get("default")
            help_text = var_def.get("help_text", "")
            click.echo(f"  • {click.style(var, fg='cyan')} (default: {default}) - {help_text}")
        click.echo()

    # Check for orphaned variables
    orphaned_vars = []
    for var in existing_vars:
        clean_var = var.replace("# ", "")
        if clean_var not in schema:
            orphaned_vars.append(clean_var)

    if orphaned_vars:
        issues_found = True
        click.echo(
            click.style("Variables in .env file not defined in schema:", fg="magenta", bold=True)
        )
        for var in orphaned_vars:
            click.echo(f"  • {click.style(var, fg='cyan')}")
        click.echo()

    # Summary
    if not issues_found:
        click.echo(click.style("✓ All variables are in sync!", fg="green", bold=True))
    else:
        click.echo(f"Run {click.style('epicenv create', fg='green')} to regenerate the .env file.")
