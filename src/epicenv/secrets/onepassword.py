"""1Password CLI secret provider implementation."""

import subprocess

from .base import SecretProvider


def check_available() -> tuple[bool, str | None]:
    """
    Check if 1Password CLI is available and user is signed in.

    Returns:
        Tuple of (is_available, error_message)
    """
    # Check 1: Is 'op' command available?
    try:
        result = subprocess.run(  # noqa: S603
            ["op", "--version"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, "1Password CLI not installed"
    except FileNotFoundError:
        return False, "1Password CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "1Password CLI not responding"
    except OSError as e:
        return False, f"Error invoking 1Password CLI: {e}"

    # Check 2: Is user signed in?
    try:
        result = subprocess.run(  # noqa: S603
            ["op", "whoami"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, "Not signed in to 1Password CLI"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "1Password CLI not responding"
    except OSError as e:
        return False, f"Error invoking 1Password CLI: {e}"


def fetch_field(reference: str, timeout: int = 10) -> tuple[str | None, str | None]:
    """
    Fetch a single field from 1Password.

    Args:
        reference: 1Password secret reference (e.g., "op://vault/item/field")
        timeout: Timeout in seconds (default: 10)

    Returns:
        Tuple of (value, error_message)
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["op", "read", reference],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            error = result.stderr.strip() or "Unknown error"
            return None, f"Failed to read secret: {error}"
        return result.stdout.strip(), None
    except subprocess.TimeoutExpired:
        return None, "Timeout reading from 1Password"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def fetch_fields(item_reference: str, fields: list[str], timeout: int = 10) -> tuple[dict[str, str] | None, str | None]:
    """
    Fetch multiple fields from a 1Password item.

    This function makes multiple calls to `op read` for each field.
    Future optimization: Use `op item get` with single call.

    Args:
        item_reference: Base item reference (e.g., "op://vault/item")
        fields: List of field names to retrieve
        timeout: Timeout per field in seconds (default: 10)

    Returns:
        Tuple of (values_dict, error_message)
        values_dict maps field names to their values
    """
    # Ensure item_reference doesn't end with a slash
    item_reference = item_reference.rstrip("/")

    values = {}
    for field in fields:
        # Construct full reference for this field
        field_reference = f"{item_reference}/{field}"

        # Fetch the field
        value, error = fetch_field(field_reference, timeout)
        if error:
            return None, f"Failed to fetch field '{field}': {error}"

        values[field] = value

    return values, None


class OnePasswordProvider(SecretProvider):
    """1Password CLI secret provider."""

    def is_available(self) -> tuple[bool, str | None]:
        """Check if 1Password CLI is available and user is signed in."""
        return check_available()

    def get_field(self, reference: str) -> tuple[str | None, str | None]:
        """Fetch a single field from 1Password."""
        return fetch_field(reference)

    def get_fields(self, reference: str, fields: list[str]) -> tuple[dict[str, str] | None, str | None]:
        """Fetch multiple fields from a 1Password item."""
        return fetch_fields(reference, fields)
