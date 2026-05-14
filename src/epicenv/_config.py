"""
Configuration loader for epicenv schema.

Schema can live in either ``pyproject.toml`` under ``[tool.epicenv.variables]``
or in a dedicated TOML file. Discovery order:

1. ``[tool.epicenv] config_file = "..."`` in ``pyproject.toml`` (path is resolved
   relative to the directory containing ``pyproject.toml``).
2. Auto-discovered ``.env.toml`` next to ``pyproject.toml``.
3. ``[tool.epicenv.variables]`` inside ``pyproject.toml`` itself.

In dedicated files, variables live under a top-level ``[variables]`` table.
Defining variables in both ``pyproject.toml`` and an external file is an error.
"""

import sys
from functools import lru_cache
from pathlib import Path

from ._exceptions import ConfigError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


EXTERNAL_CONFIG_FILENAME = ".env.toml"


def _read_toml(path: Path) -> dict:
    """Parse a TOML file and return its contents as a dict."""
    with open(path, "rb") as f:
        return tomllib.load(f)


@lru_cache(maxsize=1)
def find_pyproject_toml(start_path: Path | None = None) -> Path | None:
    """
    Search for pyproject.toml from start_path upward to root.

    Args:
        start_path: Starting directory to search from. Defaults to current working directory.

    Returns:
        Path to pyproject.toml if found, None otherwise.
    """
    current = start_path or Path.cwd()

    for parent in [current, *current.parents]:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            return pyproject

    return None


def get_schema_path(pyproject_path: Path) -> Path:
    """
    Return the file that should be parsed for the schema.

    Raises ``ConfigError`` when the user has variables defined in both
    ``pyproject.toml`` and an external file, or when ``config_file`` points to
    a missing path.
    """
    pyproject_data = _read_toml(pyproject_path)
    tool_config = pyproject_data.get("tool", {}).get("epicenv", {})
    project_root = pyproject_path.parent

    explicit = tool_config.get("config_file")
    if explicit:
        external = (project_root / explicit).resolve()
        if not external.exists():
            raise ConfigError(f"[tool.epicenv] config_file points to a missing file: {external}")
    else:
        auto = project_root / EXTERNAL_CONFIG_FILENAME
        external = auto if auto.exists() else None

    if external is not None and tool_config.get("variables"):
        raise ConfigError(
            "Schema is defined in both pyproject.toml ([tool.epicenv.variables]) "
            f"and {external}. Move all variables into one location."
        )

    return external if external is not None else pyproject_path


@lru_cache(maxsize=1)
def load_schema(pyproject_path: Path) -> dict:
    """
    Load the variable schema for the project.

    Reads the schema from whichever location applies (see module docstring).

    Args:
        pyproject_path: Path to pyproject.toml file.

    Returns:
        Dictionary of variable definitions from the schema.
    """
    source = get_schema_path(pyproject_path)
    data = _read_toml(source)

    if source == pyproject_path:
        return data.get("tool", {}).get("epicenv", {}).get("variables", {})
    return data.get("variables", {})


def get_config(pyproject_path: Path) -> dict:
    """
    Load [tool.epicenv] config (not variables) from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml file.

    Returns:
        Dictionary of configuration settings.
    """
    data = _read_toml(pyproject_path)
    tool_config = data.get("tool", {}).get("epicenv", {})
    # Remove variables from config (they're handled separately)
    return {k: v for k, v in tool_config.items() if k != "variables"}
