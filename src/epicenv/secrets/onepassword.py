"""1Password CLI secret provider implementation."""

import json
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
    except FileNotFoundError:
        return None, "1Password CLI not installed"
    except subprocess.TimeoutExpired:
        return None, "Timeout reading from 1Password"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def fetch_fields(item_reference: str, fields: list[str], timeout: int = 10) -> tuple[dict[str, str] | None, str | None]:
    """
    Fetch multiple fields from a 1Password item in a single call.

    Uses ``op item get --format json`` so the whole item is retrieved atomically —
    one subprocess invocation per item regardless of how many fields are requested.
    Fields are matched first by ``label``, then by ``id``.

    Args:
        item_reference: Base item reference (e.g., "op://vault/item")
        fields: List of field labels (or ids) to retrieve
        timeout: Timeout in seconds (default: 10)

    Returns:
        Tuple of (values_dict, error_message)
        values_dict maps the requested names to their values.
    """
    item_reference = item_reference.rstrip("/")

    if not fields:
        return {}, None

    # `op item get` doesn't accept `op://vault/item` references — it wants the item
    # name/UUID with `--vault` as a separate flag. Parse the reference if present.
    cmd = ["op", "item", "get"]
    if item_reference.startswith("op://"):
        parts = item_reference[len("op://") :].split("/")
        if len(parts) != 2 or not all(parts):
            return None, f"Invalid item reference '{item_reference}' (expected 'op://vault/item')"
        vault, item = parts
        cmd += [item, "--vault", vault]
    else:
        cmd.append(item_reference)
    cmd += ["--format", "json"]

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            error = result.stderr.strip() or "Unknown error"
            return None, f"Failed to read item: {error}"
    except FileNotFoundError:
        return None, "1Password CLI not installed"
    except subprocess.TimeoutExpired:
        return None, "Timeout reading from 1Password"
    except Exception as e:
        return None, f"Unexpected error: {e}"

    try:
        item = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON from 1Password: {e}"

    by_label: dict[str, str] = {}
    by_id: dict[str, str] = {}
    for f in item.get("fields", []):
        value = f.get("value")
        if value is None:
            continue
        label = f.get("label")
        field_id = f.get("id")
        if label:
            by_label[label] = value
        if field_id:
            by_id[field_id] = value

    values: dict[str, str] = {}
    for field in fields:
        if field in by_label:
            values[field] = by_label[field]
        elif field in by_id:
            values[field] = by_id[field]
        else:
            return None, f"Field '{field}' not found in item"

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
