"""Secrets CLI command implementation."""

import json
import sys

import click

from ..secrets.onepassword import OnePasswordProvider


def get_secrets(reference: str, fields: str | None, format: str, silent: bool):
    """
    Retrieve secrets from 1Password.

    Args:
        reference: 1Password reference (e.g., "op://vault/item" or "op://vault/item/field")
        fields: Comma-separated list of field names to retrieve
        format: Output format - json, env, or plain
        silent: If True, suppress warnings
    """
    # Initialize provider
    provider = OnePasswordProvider()

    # Check availability
    available, error = provider.is_available()
    if not available:
        click.echo(click.style("Error: ", fg="red", bold=True) + "1Password CLI not available", err=True)
        click.echo(f"\nReason: {error}", err=True)
        click.echo("\nSetup instructions:", err=True)
        click.echo("  1. Install: https://developer.1password.com/docs/cli/get-started/", err=True)
        click.echo("  2. Sign in: op signin", err=True)
        sys.exit(1)

    # Parse fields
    field_list = [f.strip() for f in fields.split(",")] if fields else None

    # Fetch secrets
    if field_list:
        # Multiple fields
        values, error = provider.get_fields(reference, field_list)
        if error:
            click.echo(click.style("Error: ", fg="red", bold=True) + error, err=True)
            sys.exit(1)
    else:
        # Single field - reference should include the field
        value, error = provider.get_field(reference)
        if error:
            click.echo(click.style("Error: ", fg="red", bold=True) + error, err=True)
            sys.exit(1)
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
