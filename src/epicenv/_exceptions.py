"""Custom exceptions for epicenv."""

from pathlib import Path


class EpicenvError(Exception):
    """Base exception for epicenv."""

    pass


class UndefinedVariableError(EpicenvError, ValueError):
    """Raised when accessing an environment variable not defined in schema."""

    def __init__(self, var_name: str, schema_path: Path | None = None):
        """Initialize the exception with a helpful error message.

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
