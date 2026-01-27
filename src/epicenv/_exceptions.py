"""Custom exceptions for epicenv."""

from pathlib import Path


class EpicenvError(Exception):
    """Base exception for epicenv."""

    pass


class UndefinedVariableError(EpicenvError, ValueError):
    """Raised when accessing an environment variable not defined in schema."""

    def __init__(self, var_name: str, schema_path: Path | None = None):
        """
        Initialize the exception with a helpful error message.

        Args:
            var_name: Name of the undefined environment variable.
            schema_path: Path to the pyproject.toml file (if known).
        """
        msg = (
            f"Environment variable '{var_name}' is not defined in pyproject.toml schema.\n\n"
            f"Add it to [tool.epicenv.variables] in your pyproject.toml:\n\n"
            f"[tool.epicenv.variables]\n"
            f'{var_name} = {{ type = "str", help_text = "Description here" }}\n\n'
            f"Or disable validation by setting EPICENV_VALIDATE=off"
        )
        if schema_path:
            msg += f"\n\nSchema file: {schema_path}"

        super().__init__(msg)


class DjangoNotAvailableError(EpicenvError):
    """Raised when Django is required but not available."""

    def __init__(self, reason: str = "Django is not installed"):
        msg = (
            f"{reason}\n\n"
            "The create-superuser command requires Django to be installed.\n"
            "Install it with: pip install django"
        )
        super().__init__(msg)


class DatabaseNotReadyError(EpicenvError):
    """Raised when the database is not accessible."""

    def __init__(self, reason: str):
        msg = (
            f"Database is not ready: {reason}\n\n"
            "Make sure:\n"
            "1. Your database is running\n"
            "2. Django settings are configured correctly\n"
            "3. Migrations have been applied: python manage.py migrate"
        )
        super().__init__(msg)


class OnePasswordCredentialError(EpicenvError):
    """Raised when 1Password credentials cannot be fetched."""

    def __init__(self, reference: str, field: str, reason: str):
        msg = (
            f"Failed to fetch '{field}' from 1Password.\n"
            f"Reference: {reference}/{field}\n"
            f"Reason: {reason}\n\n"
            "Make sure:\n"
            "1. 1Password CLI is installed and you're signed in\n"
            "2. The reference path exists in your vault\n"
            "3. The item has username, email, and password fields"
        )
        super().__init__(msg)
