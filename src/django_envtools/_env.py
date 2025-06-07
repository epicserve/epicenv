import importlib
import sys
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import environs

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
    ):
        self.var_data = {}
        self._env = environs.Env(eager=eager, expand_vars=expand_vars)

    @staticmethod
    def _get_var(
        environs_instance,
        var_type: str,
        environ_args: tuple[Any, ...],
        environ_kwargs: dict[str, Any] | None = None,
    ):
        environ_kwargs = environ_kwargs or {}
        help_text = environ_kwargs.pop("help_text", None)
        initial = environ_kwargs.pop("initial", None)
        initial_func = environ_kwargs.pop("initial_func", None)

        if _is_command_or_test() is True:
            env_variables[environ_args[0]] = {
                "type": var_type,
                "default": environ_kwargs.get("default"),
                "help_text": help_text,
                "initial": initial,
                "initial_func": initial_func,
            }

        try:
            return getattr(environs_instance, var_type)(*environ_args, **environ_kwargs)
        except environs.EnvError:
            if _is_command_or_test() is False:
                raise

    def __call__(self, *args, **kwargs):
        return self._get_var(self._env, var_type="str", environ_args=args, environ_kwargs=kwargs)

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

        def _get_var(*args, **kwargs):
            return self._get_var(self._env, var_type=item, environ_args=args, environ_kwargs=kwargs)

        return _get_var

    def read_env(self, *args, **kwargs) -> bool:
        return self._env.read_env(*args, **kwargs)


def get_dot_env_file_str() -> str:
    env_str = (
        f"# This is an initial .env file generated on {datetime.now(UTC).isoformat()}. Any environment variable with a default\n"  # noqa: E501
        "# can be safely removed or commented out. Any variable without a default must be set.\n\n"
    )
    for key, data in env_variables.items():
        initial = data.get("initial", None)
        initial_func = data.get("initial_func", None)
        val = ""

        if data["help_text"] is not None:
            env_str += f"# {data['help_text']}\n"
        env_str += f"# type: {data['type']}\n"

        if data["default"] is not None:
            env_str += f"# default: {data['default']}\n"

        if initial_func:
            if callable(initial_func):
                val = initial_func()
            elif isinstance(initial_func, str):
                val = get_callable(initial_func)()
        elif initial is not None:
            val = initial

        if val == "" and data["default"] is not None:
            env_str += f"# {key}={val}\n\n"
        else:
            env_str += f"{key}={val}\n\n"
    return env_str


def get_callable(namespace_str):
    module_name, func_name = namespace_str.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)
