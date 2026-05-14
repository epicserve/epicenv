"""Tests for external schema file support (.env.toml / config_file)."""

import pytest

from epicenv._config import find_pyproject_toml, load_schema
from epicenv._exceptions import ConfigError


@pytest.fixture(autouse=True)
def clear_config_caches():
    """Clear lru_caches so each test sees a fresh load."""
    find_pyproject_toml.cache_clear()
    load_schema.cache_clear()
    yield
    find_pyproject_toml.cache_clear()
    load_schema.cache_clear()


def _write_minimal_pyproject(tmp_path, extra: str = "") -> "pytest.PathLike":
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\nversion = "0.0.0"\n' + extra)
    return pyproject


class TestBackwardsCompat:
    def test_pyproject_only_schema_still_loads(self, tmp_path):
        pyproject = _write_minimal_pyproject(
            tmp_path,
            extra=('\n[tool.epicenv.variables]\nSECRET_KEY = { type = "str", required = true }\n'),
        )

        schema = load_schema(pyproject)

        assert "SECRET_KEY" in schema
        assert schema["SECRET_KEY"]["type"] == "str"

    def test_pyproject_with_no_epicenv_section_returns_empty(self, tmp_path):
        pyproject = _write_minimal_pyproject(tmp_path)

        assert load_schema(pyproject) == {}


class TestAutoDiscovery:
    def test_env_toml_is_auto_discovered(self, tmp_path):
        pyproject = _write_minimal_pyproject(tmp_path)
        (tmp_path / ".env.toml").write_text('[variables]\nAPI_KEY = { type = "str", required = true }\n')

        schema = load_schema(pyproject)

        assert "API_KEY" in schema
        assert schema["API_KEY"]["required"] is True

    def test_table_form_and_inline_form_are_equivalent(self, tmp_path):
        pyproject = _write_minimal_pyproject(tmp_path)
        (tmp_path / ".env.toml").write_text(
            "[variables]\n"
            'INLINE = { type = "str", required = true, help_text = "h" }\n'
            "\n"
            "[variables.TABLE]\n"
            'type = "str"\n'
            "required = true\n"
            'help_text = "h"\n'
        )

        schema = load_schema(pyproject)

        assert schema["INLINE"] == schema["TABLE"]


class TestExplicitConfigFile:
    def test_explicit_config_file_overrides_auto_discovery(self, tmp_path):
        pyproject = _write_minimal_pyproject(
            tmp_path,
            extra='\n[tool.epicenv]\nconfig_file = "config/env.toml"\n',
        )
        (tmp_path / ".env.toml").write_text('[variables]\nWRONG = { type = "str" }\n')
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "env.toml").write_text('[variables]\nRIGHT = { type = "str" }\n')

        schema = load_schema(pyproject)

        assert "RIGHT" in schema
        assert "WRONG" not in schema

    def test_missing_explicit_config_file_raises(self, tmp_path):
        pyproject = _write_minimal_pyproject(
            tmp_path,
            extra='\n[tool.epicenv]\nconfig_file = "missing.toml"\n',
        )

        with pytest.raises(ConfigError, match="missing.toml"):
            load_schema(pyproject)


class TestConflict:
    def test_inline_and_auto_discovered_external_conflict(self, tmp_path):
        pyproject = _write_minimal_pyproject(
            tmp_path,
            extra=('\n[tool.epicenv.variables]\nX = { type = "str" }\n'),
        )
        (tmp_path / ".env.toml").write_text('[variables]\nY = { type = "str" }\n')

        with pytest.raises(ConfigError, match="both"):
            load_schema(pyproject)

    def test_inline_and_explicit_external_conflict(self, tmp_path):
        pyproject = _write_minimal_pyproject(
            tmp_path,
            extra=('\n[tool.epicenv]\nconfig_file = "schema.toml"\n\n[tool.epicenv.variables]\nX = { type = "str" }\n'),
        )
        (tmp_path / "schema.toml").write_text('[variables]\nY = { type = "str" }\n')

        with pytest.raises(ConfigError, match="both"):
            load_schema(pyproject)
