"""Secrets CLI command implementation."""

import json
import sys

import click

from ..secrets.onepassword import OnePasswordProvider


def _looks_like_setup_issue(error: str) -> bool:
    """Detect errors from `op` that indicate install/sign-in issues, not item lookups."""
    needles = ("not installed", "not currently signed in", "not signed in", "you aren't currently signed in")
    return any(n in error.lower() for n in (needle.lower() for needle in needles))


def _exit_with_error(error: str):
    click.echo(click.style("Error: ", fg="red", bold=True) + error, err=True)
    if _looks_like_setup_issue(error):
        click.echo("\nSetup instructions:", err=True)
        click.echo("  1. Install: https://developer.1password.com/docs/cli/get-started/", err=True)
        click.echo("  2. Sign in: op signin", err=True)
    sys.exit(1)


def get_secrets(reference: str, fields: str | None, format: str, silent: bool):
    """
    Retrieve secrets from 1Password.

    Args:
        reference: 1Password reference (e.g., "op://vault/item" or "op://vault/item/field")
        fields: Comma-separated list of field names to retrieve
        format: Output format - json, env, or plain
        silent: If True, suppress warnings
    """
    provider = OnePasswordProvider()

    # Parse fields
    field_list = [f.strip() for f in fields.split(",")] if fields else None

    # Fetch secrets — no eager availability check; install/sign-in problems are
    # surfaced reactively from the real `op` call.
    if field_list:
        values, error = provider.get_fields(reference, field_list)
        if error:
            _exit_with_error(error)
    else:
        # Single field - reference should include the field
        value, error = provider.get_field(reference)
        if error:
            _exit_with_error(error)
        # Wrap in dict for consistent handling
        values = {"value": value}

    # Format output
    if format == "json":
        click.echo(json.dumps(values))
    elif format == "env":
        for key, value in values.items():
            click.echo(f"{key.upper()}={value}")
    elif format == "plain":
        if len(values) == 1:
            # Output just the value
            click.echo(list(values.values())[0])
        else:
            click.echo(
                click.style("Error: ", fg="red", bold=True) + "Plain format only supports single field",
                err=True,
            )
            click.echo("Use --format json or --format env for multiple fields", err=True)
            sys.exit(1)
