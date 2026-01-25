import importlib
import os
import sys
import warnings
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import environs

from ._config import find_pyproject_toml, load_schema
from ._exceptions import UndefinedVariableError

env_variables: dict[str, Any] = {}

MANAGEMENT_COMMANDS = ["create_env_file", "diff_env_file", "pytest"]


@lru_cache
def _is_command_or_test():
    is_test = any([arg.startswith("test_") for arg in sys.argv])
    is_command = any(arg.endswith(command) for command in MANAGEMENT_COMMANDS for arg in sys.argv)
    return is_command or is_test


class Env:
    var_data: dict[str, Any]
    write_dot_env_file: bool = False
    base_dir: Path

    def __init__(
        self,
        eager: bool = True,
        expand_vars: bool = False,
        schema_path: Path | None = None,
    ):
        """Initialize the Env instance.

        Args:
            eager: If True, eagerly parse .env file. Passed to environs.Env.
            expand_vars: If True, expand variables in .env file. Passed to environs.Env.
            schema_path: Optional path to pyproject.toml. If None, searches from cwd upward.
        """
        self.var_data = {}
        self._env = environs.Env(eager=eager, expand_vars=expand_vars)
        self._schema_path = schema_path
        self._schema = None  # Lazy loaded
        self._schema_file_path = None

    def _load_schema(self):
        """Load schema from pyproject.toml (lazy, cached)."""
        if self._schema is not None:
            return

        schema_path = self._schema_path or find_pyproject_toml()
        if schema_path and schema_path.exists():
            self._schema = load_schema(schema_path)
            self._schema_file_path = schema_path
        else:
            self._schema = {}
            self._schema_file_path = None

    def _should_validate(self) -> bool | str:
        """Determine validation mode based on EPICENV_VALIDATE environment variable.

        Returns:
            Validation mode: "strict", "warn", or "off"
        """
        # Read from EPICENV_VALIDATE env var (default: "auto")
        validate_mode = os.getenv("EPICENV_VALIDATE", "auto").lower()

        # Validate the mode value
        if validate_mode not in ("auto", "strict", "warn", "off"):
            warnings.warn(
                f"Invalid EPICENV_VALIDATE value '{validate_mode}'. "
                f"Valid values: auto, strict, warn, off. Defaulting to 'auto'.",
                UserWarning,
                stacklevel=2,
            )
            validate_mode = "auto"

        # Handle "auto" mode: validate when DEBUG is true
        if validate_mode == "auto":
            debug = os.getenv("DEBUG", "").lower() in ("1", "true", "on", "yes")
            return "strict" if debug else "off"

        return validate_mode

    def _get_var(
        self,
        var_type: str,
        environ_args: tuple[Any, ...],
        environ_kwargs: dict[str, Any] | None = None,
    ):
        """Get an environment variable with optional validation against schema.

        Args:
            var_type: Type of variable (str, bool, int, etc.)
            environ_args: Positional args to pass to environs method
            environ_kwargs: Keyword args to pass to environs method

        Returns:
            The parsed environment variable value

        Raises:
            UndefinedVariableError: If validation is enabled and variable not in schema
        """
        environ_kwargs = environ_kwargs or {}
        var_name = environ_args[0]

        # Extract custom parameters
        help_text = environ_kwargs.pop("help_text", None)
        initial = environ_kwargs.pop("initial", None)
        initial_func = environ_kwargs.pop("initial_func", None)

        # Load schema for validation
        self._load_schema()

        # Validate against schema if enabled
        validation_mode = self._should_validate()
        if validation_mode != "off" and var_name not in self._schema:
            if validation_mode == "warn":
                warnings.warn(
                    f"Environment variable '{var_name}' is not defined in pyproject.toml schema",
                    UserWarning,
                    stacklevel=3,
                )
            elif validation_mode == "strict":
                raise UndefinedVariableError(var_name, self._schema_file_path)

        # For schema-defined vars, merge schema defaults with code defaults
        if var_name in self._schema:
            schema_def = self._schema[var_name]
            # Apply defaults from schema if not provided in code
            if "default" in schema_def and "default" not in environ_kwargs:
                environ_kwargs["default"] = schema_def["default"]

        # Track variable for CLI commands (backward compat)
        if _is_command_or_test():
            env_variables[var_name] = {
                "type": var_type,
                "default": environ_kwargs.get("default"),
                "help_text": help_text,
                "initial": initial,
                "initial_func": initial_func,
            }

        try:
            return getattr(self._env, var_type)(*environ_args, **environ_kwargs)
        except environs.EnvError:
            if _is_command_or_test() is False:
                raise

    def __call__(self, *args, **kwargs):
        return self._get_var(var_type="str", environ_args=args, environ_kwargs=kwargs)

    def __getattr__(self, item):
        allowed_methods = [
            "bool",
            "date",
            "datetime",
            "decimal",
            "dict",
            "dj_cache_url",
            "dj_db_url",
            "dj_email_url",
            "enum",
            "float",
            "int",
            "json",
            "list",
            "log_level",
            "path",
            "read_env",
            "str",
            "time",
            "timedelta",
            "url",
            "uuid",
        ]
        if item not in allowed_methods:
            return AttributeError(f"'{type(self).__name__}' object has no attribute '{item}'")

        def _get_var_wrapper(*args, **kwargs):
            return self._get_var(var_type=item, environ_args=args, environ_kwargs=kwargs)

        return _get_var_wrapper

    def read_env(self, *args, **kwargs) -> bool:
        return self._env.read_env(*args, **kwargs)


def get_dot_env_file_str() -> str:
    """Generate a .env file string from either schema or runtime registration.

    Tries to load from pyproject.toml schema first, falls back to runtime-registered
    env_variables dict (for backward compatibility with Django management commands).

    Returns:
        String content for .env file
    """
    env_str = (
        f"# This is an initial .env file generated on {datetime.now(UTC).isoformat()}. Any environment variable with a default\n"  # noqa: E501
        "# can be safely removed or commented out. Any variable without a default must be set.\n\n"
    )

    # Try to load from schema first
    schema_path = find_pyproject_toml()
    variables_to_process = {}

    if schema_path and schema_path.exists():
        # Load from schema
        schema = load_schema(schema_path)
        for key, schema_def in schema.items():
            variables_to_process[key] = {
                "type": schema_def.get("type", "str"),
                "default": schema_def.get("default"),
                "help_text": schema_def.get("help_text"),
                "initial": schema_def.get("initial"),
                "initial_func": schema_def.get("initial_func"),
            }

    # Fall back to or merge with runtime-registered variables
    if not variables_to_process and env_variables:
        variables_to_process = env_variables
    elif env_variables:
        # Merge: runtime registration takes precedence for values that exist in both
        for key, data in env_variables.items():
            if key not in variables_to_process:
                variables_to_process[key] = data

    for key, data in variables_to_process.items():
        initial = data.get("initial")
        initial_func = data.get("initial_func")
        val = ""

        if data.get("help_text") is not None:
            env_str += f"# {data['help_text']}\n"
        env_str += f"# type: {data['type']}\n"

        if data.get("default") is not None:
            env_str += f"# default: {data['default']}\n"

        if initial_func:
            if callable(initial_func):
                val = initial_func()
            elif isinstance(initial_func, str):
                val = get_callable(initial_func)()
        elif initial is not None:
            val = initial

        if val == "" and data.get("default") is not None:
            env_str += f"# {key}={val}\n\n"
        else:
            env_str += f"{key}={val}\n\n"
    return env_str


def get_callable(namespace_str):
    module_name, func_name = namespace_str.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)
