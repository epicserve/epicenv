"""Validate command for checking environment against schema."""

import os
import sys

import click

from .._config import find_pyproject_toml, load_schema


def validate_env(strict: bool):
    """Validate current environment variables against schema.

    Args:
        strict: If True, exit with error code on validation failure
    """
    # Find pyproject.toml
    pyproject_path = find_pyproject_toml()
    if not pyproject_path:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Could not find pyproject.toml. Make sure you're in a Python project directory."
        )
        if strict:
            sys.exit(1)
        raise click.Abort()

    # Load schema
    schema = load_schema(pyproject_path)
    if not schema:
        click.echo(
            click.style("Warning: ", fg="yellow", bold=True)
            + "No [tool.epicenv.variables] section found in pyproject.toml"
        )
        return

    click.echo(f"Validating environment against: {click.style(str(pyproject_path), fg='cyan')}\n")

    # Check each required variable
    missing_required = []
    missing_optional = []
    validation_passed = True

    for var_name, var_def in schema.items():
        has_default = var_def.get("default") is not None
        is_required = var_def.get("required", not has_default)
        is_set = var_name in os.environ

        if not is_set:
            if is_required and not has_default:
                missing_required.append((var_name, var_def))
                validation_passed = False
            elif has_default:
                missing_optional.append((var_name, var_def))

    # Report results
    if missing_required:
        click.echo(click.style("✗ Missing required variables:", fg="red", bold=True))
        for var_name, var_def in missing_required:
            help_text = var_def.get("help_text", "")
            var_type = var_def.get("type", "str")
            click.echo(f"  • {click.style(var_name, fg='yellow')} ({var_type}) - {help_text}")
        click.echo()

    if missing_optional:
        click.echo(click.style("Missing optional variables (will use defaults):", fg="yellow"))
        for var_name, var_def in missing_optional:
            default = var_def.get("default")
            var_type = var_def.get("type", "str")
            click.echo(f"  • {click.style(var_name, fg='cyan')} ({var_type}) - default: {default}")
        click.echo()

    # Summary
    if validation_passed:
        total_vars = len(schema)
        set_vars = sum(1 for var_name in schema if var_name in os.environ)
        click.echo(
            click.style("✓ Validation passed!", fg="green", bold=True)
            + f" ({set_vars}/{total_vars} variables set)"
        )
    else:
        click.echo(
            click.style("✗ Validation failed.", fg="red", bold=True)
            + f" {len(missing_required)} required variable(s) missing."
        )
        if strict:
            sys.exit(1)
