"""Tests for the `epicenv create` CLI command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from epicenv._config import find_pyproject_toml, load_schema
from epicenv.cli.main import cli


@pytest.fixture(autouse=True)
def clear_config_caches():
    """Clear lru_caches so each test sees a fresh load."""
    find_pyproject_toml.cache_clear()
    load_schema.cache_clear()
    yield
    find_pyproject_toml.cache_clear()
    load_schema.cache_clear()


def _write_schema(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "demo"\n'
        'version = "0.0.0"\n'
        "\n"
        "[tool.epicenv.variables]\n"
        'DEBUG = { type = "bool", default = false, initial = "on" }\n'
    )


class TestCreateMiseHint:
    def test_success_prints_mise_hint_for_default_path(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _write_schema(Path.cwd())
            find_pyproject_toml.cache_clear()
            result = runner.invoke(cli, ["create"])

        assert result.exit_code == 0
        assert "Created .env" in result.output
        assert '[env] _.file = ".env"' in result.output
        assert "mise.toml" in result.output

    def test_success_prints_mise_hint_for_custom_path(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _write_schema(Path.cwd())
            Path("config").mkdir()
            find_pyproject_toml.cache_clear()
            result = runner.invoke(cli, ["create", "--path", "config/.env"])

        assert result.exit_code == 0
        assert "Created config/.env" in result.output
        assert '[env] _.file = "config/.env"' in result.output
