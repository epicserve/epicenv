"""Configuration loader for pyproject.toml schema."""

import sys
from functools import lru_cache
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@lru_cache(maxsize=1)
def find_pyproject_toml(start_path: Path | None = None) -> Path | None:
    """Search for pyproject.toml from start_path upward to root.

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


@lru_cache(maxsize=1)
def load_schema(pyproject_path: Path) -> dict:
    """Load [tool.epicenv.variables] from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml file.

    Returns:
        Dictionary of variable definitions from the schema.
    """
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    return data.get("tool", {}).get("epicenv", {}).get("variables", {})


def get_config(pyproject_path: Path) -> dict:
    """Load [tool.epicenv] config (not variables) from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml file.

    Returns:
        Dictionary of configuration settings.
    """
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    tool_config = data.get("tool", {}).get("epicenv", {})
    # Remove variables from config (they're handled separately)
    config = {k: v for k, v in tool_config.items() if k != "variables"}
    return config
