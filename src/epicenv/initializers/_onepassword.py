"""
1Password CLI integration initializer.

This module provides backward compatibility for the onepassword() initializer function.
The core 1Password functionality has been refactored into the secrets.onepassword module.
"""

import sys

# Import from new secrets module
from ..secrets.onepassword import check_available as _check_onepassword_available
from ..secrets.onepassword import fetch_field as _fetch_from_onepassword


def _generate_fallback_placeholder(variable_name: str | None) -> str:
    """
    Generate a fallback placeholder for when 1Password is unavailable.

    Args:
        variable_name: The environment variable name

    Returns:
        A placeholder string like "[Enter VARIABLE_NAME]"
    """
    if variable_name:
        return f"[Enter {variable_name}]"
    return "[Enter 1Password credential]"


def _print_warning(
    reference: str,
    variable_name: str | None,
    error: str | None,
    fallback: str,
) -> None:
    """
    Print warning about 1Password unavailability to stderr.

    Args:
        reference: The 1Password reference that was attempted
        variable_name: The environment variable name
        error: The error message describing why 1Password is unavailable
        fallback: The fallback value being used
    """
    # Try to use click for colored output, fall back to plain print
    try:
        import click

        var_text = f" for {variable_name}" if variable_name else ""
        click.echo(
            click.style(f"\n⚠️  1Password CLI not available{var_text}", fg="yellow"),
            err=True,
        )
        click.echo(f"  Reference: {reference}", err=True)
        if error:
            click.echo(f"  Reason: {error}", err=True)
        click.echo(f"  Using fallback: {fallback}", err=True)
        click.echo("\n  Setup instructions:", err=True)
        click.echo(
            "  1. Install: https://developer.1password.com/docs/cli/get-started/",
            err=True,
        )
        click.echo("  2. Sign in: op signin", err=True)
        click.echo("  3. Regenerate: epicenv create --overwrite\n", err=True)
    except ImportError:
        # Fallback to plain print if click is not available
        var_text = f" for {variable_name}" if variable_name else ""
        print(f"\n⚠️  1Password CLI not available{var_text}", file=sys.stderr)
        print(f"  Reference: {reference}", file=sys.stderr)
        if error:
            print(f"  Reason: {error}", file=sys.stderr)
        print(f"  Using fallback: {fallback}", file=sys.stderr)
        print("\n  Setup instructions:", file=sys.stderr)
        print(
            "  1. Install: https://developer.1password.com/docs/cli/get-started/",
            file=sys.stderr,
        )
        print("  2. Sign in: op signin", file=sys.stderr)
        print("  3. Regenerate: epicenv create --overwrite\n", file=sys.stderr)


def onepassword(
    reference: str,
    fallback: str | None = None,
    *,
    silent: bool = False,
    _variable_name: str | None = None,
) -> str:
    """
    Fetch a secret from 1Password CLI using a secret reference.

    This function attempts to fetch a secret from 1Password using the 'op' CLI tool.
    If 1Password is unavailable or the fetch fails, it returns a fallback value.
    By default, it generates a descriptive placeholder based on the variable name,
    but you can provide a custom fallback value.

    Args:
        reference: 1Password secret reference in format "op://vault/item/[section/]field"
                  Example: "op://Development/API Keys/production/token"
        fallback: Optional fallback value when 1Password is unavailable.
                 If None, generates "[Enter VARIABLE_NAME]" using _variable_name.
        silent: If True, suppresses warning messages. Default: False.
        _variable_name: Internal parameter auto-populated with the environment variable name.
                       Used to generate descriptive fallback placeholders.

    Returns:
        The secret value from 1Password, or fallback value if unavailable.

    Example:
        In pyproject.toml:
        ```toml
        [tool.epicenv.variables]
        STRIPE_API_KEY = {
            type = "str",
            required = true,
            initial_func = "epicenv.initializers.onepassword",
            args = ["op://Production/Stripe/api_key"]
        }

        # With custom fallback:
        DATABASE_PASSWORD = {
            type = "str",
            required = true,
            initial_func = "epicenv.initializers.onepassword",
            args = ["op://Production/Database/password"],
            kwargs = { fallback = "local_dev_password" }
        }
        ```
    """
    # Step 1: Check if 1Password is available
    is_available, error = _check_onepassword_available()

    if is_available:
        # Step 2: Try to fetch from 1Password
        value, fetch_error = _fetch_from_onepassword(reference)
        if value:
            return value
        # Fetch failed, fall through to fallback
        error = fetch_error

    # Step 3: Use fallback
    final_value = fallback if fallback is not None else _generate_fallback_placeholder(_variable_name)

    # Step 4: Show warning (unless silent)
    if not silent:
        _print_warning(reference, _variable_name, error, final_value)

    return final_value
