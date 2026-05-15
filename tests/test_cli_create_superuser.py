"""Tests for the `epicenv create-superuser` CLI command."""

import pytest
from click.testing import CliRunner

from epicenv.cli.main import cli


@pytest.fixture
def patched_framework(mocker):
    """Patch the framework-level Django functions so tests don't need a real DB."""
    integration = mocker.MagicMock()
    integration.is_available.return_value = (True, None)
    mocker.patch(
        "epicenv.cli.create_superuser.DjangoSuperuserIntegration",
        return_value=integration,
    )
    mocker.patch("epicenv.cli.create_superuser.setup_django")
    user_exists = mocker.patch(
        "epicenv.cli.create_superuser.user_exists", return_value=False
    )
    create = mocker.patch("epicenv.cli.create_superuser.create_superuser_record")
    update = mocker.patch("epicenv.cli.create_superuser.update_superuser_record")
    # The CLI uses select.select() to peek at stdin; stub it to report "ready" only
    # when CliRunner's underlying BytesIO actually contains input. select() can't
    # operate on the in-memory streams CliRunner installs.
    def _select_stub(rlist, _w, _x, _t):
        ready = []
        for stream in rlist:
            buf = getattr(stream, "buffer", stream)
            data = getattr(buf, "getvalue", lambda: b"")()
            if data:
                ready.append(stream)
        return (ready, [], [])

    mocker.patch("select.select", side_effect=_select_stub)
    return {
        "integration": integration,
        "user_exists": user_exists,
        "create": create,
        "update": update,
    }


class TestInputSourceDetection:
    def test_explicit_flags(self, patched_framework):
        result = CliRunner().invoke(
            cli,
            [
                "create-superuser",
                "--username", "admin",
                "--email", "admin@example.com",
                "--password", "secret",
            ],
        )
        assert result.exit_code == 0, result.output
        patched_framework["create"].assert_called_once_with(
            "admin", "admin@example.com", "secret", "default"
        )

    def test_stdin_json(self, patched_framework):
        result = CliRunner().invoke(
            cli,
            ["create-superuser"],
            input='{"username": "admin", "email": "admin@example.com", "password": "secret"}',
        )
        assert result.exit_code == 0, result.output
        patched_framework["create"].assert_called_once_with(
            "admin", "admin@example.com", "secret", "default"
        )

    def test_env_vars(self, patched_framework, monkeypatch):
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "secret")
        # No stdin input → select stub reports not-ready → falls through to env vars
        result = CliRunner().invoke(cli, ["create-superuser"])
        assert result.exit_code == 0, result.output
        patched_framework["create"].assert_called_once_with(
            "admin", "admin@example.com", "secret", "default"
        )

    def test_no_input_shows_help(self, patched_framework, monkeypatch):
        for key in ("DJANGO_SUPERUSER_USERNAME", "DJANGO_SUPERUSER_EMAIL", "DJANGO_SUPERUSER_PASSWORD"):
            monkeypatch.delenv(key, raising=False)
        result = CliRunner().invoke(cli, ["create-superuser"])
        assert result.exit_code == 1
        assert "No credentials provided" in result.output


class TestStdinValidation:
    def test_invalid_json(self, patched_framework):
        result = CliRunner().invoke(
            cli, ["create-superuser"], input="this is not json"
        )
        assert result.exit_code == 1
        assert "Invalid JSON from stdin" in result.output

    def test_missing_fields_in_json(self, patched_framework):
        result = CliRunner().invoke(
            cli, ["create-superuser"], input='{"username": "admin"}'
        )
        assert result.exit_code == 1
        assert "Missing required fields" in result.output
        assert "email" in result.output
        assert "password" in result.output


class TestEnvVarValidation:
    def test_partial_env_vars(self, patched_framework, monkeypatch):
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin")
        monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
        monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
        result = CliRunner().invoke(cli, ["create-superuser"])
        assert result.exit_code == 1
        assert "Missing environment variables" in result.output
        assert "DJANGO_SUPERUSER_EMAIL" in result.output


class TestDjangoAvailability:
    def test_django_not_installed(self, patched_framework):
        patched_framework["integration"].is_available.return_value = (
            False,
            "Django is not installed",
        )
        result = CliRunner().invoke(
            cli,
            [
                "create-superuser",
                "--username", "admin",
                "--email", "a@b.c",
                "--password", "secret",
            ],
        )
        assert result.exit_code == 1
        assert "Django is not installed" in result.output
        assert "pip install django" in result.output


class TestIdempotency:
    def test_user_already_exists_returns_zero(self, patched_framework):
        patched_framework["user_exists"].return_value = True
        result = CliRunner().invoke(
            cli,
            [
                "create-superuser",
                "--username", "admin",
                "--email", "a@b.c",
                "--password", "secret",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "already exists" in result.output
        patched_framework["create"].assert_not_called()
        patched_framework["update"].assert_not_called()

    def test_force_updates_existing_user(self, patched_framework):
        patched_framework["user_exists"].return_value = True
        result = CliRunner().invoke(
            cli,
            [
                "create-superuser",
                "--username", "admin",
                "--email", "new@example.com",
                "--password", "newpass",
                "--force",
            ],
        )
        assert result.exit_code == 0, result.output
        patched_framework["update"].assert_called_once_with(
            "admin", "new@example.com", "newpass", "default"
        )
        patched_framework["create"].assert_not_called()

    def test_creates_new_user_when_missing(self, patched_framework):
        patched_framework["user_exists"].return_value = False
        result = CliRunner().invoke(
            cli,
            [
                "create-superuser",
                "--username", "admin",
                "--email", "a@b.c",
                "--password", "secret",
            ],
        )
        assert result.exit_code == 0, result.output
        patched_framework["create"].assert_called_once()
        patched_framework["update"].assert_not_called()


class TestDatabaseErrors:
    def test_user_exists_lookup_fails(self, patched_framework):
        patched_framework["user_exists"].side_effect = RuntimeError("table missing")
        result = CliRunner().invoke(
            cli,
            [
                "create-superuser",
                "--username", "admin",
                "--email", "a@b.c",
                "--password", "secret",
            ],
        )
        assert result.exit_code == 1
        assert "Database error" in result.output
        assert "table missing" in result.output

    def test_custom_database_alias_passed_through(self, patched_framework):
        result = CliRunner().invoke(
            cli,
            [
                "create-superuser",
                "--username", "admin",
                "--email", "a@b.c",
                "--password", "secret",
                "--database", "other",
            ],
        )
        assert result.exit_code == 0, result.output
        patched_framework["user_exists"].assert_called_once_with("admin", "other")
        patched_framework["create"].assert_called_once_with("admin", "a@b.c", "secret", "other")
