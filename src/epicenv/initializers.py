"""Initializer functions for generating initial .env values."""

import secrets
import string


def url_safe_password(length: int = 50) -> str:
    """
    Generate a URL-safe random password.

    Args:
        length: The length of the password to generate. Defaults to 50.

    Returns:
        A URL-safe random string containing letters, digits, and the characters '-_'.
    """
    # URL-safe characters: alphanumeric plus hyphen and underscore
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))
