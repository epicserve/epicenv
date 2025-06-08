from pathlib import Path

import pytest


@pytest.fixture
def clean_env_files():
    """Remove .env* files from a specific directory."""
    yield

    cwd = Path.cwd()
    for env_file in cwd.glob(".env*"):
        env_file.unlink()
