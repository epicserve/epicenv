"""Tests for the create-superuser CLI command."""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from epicenv.cli.create_superuser import (
    SuperuserCredentials,
    _create_or_update_superuser,
    _fetch_superuser_credentials,
)
from epicenv.cli.main import cli


class TestCreateSuperuserCommand:
    """Tests for the create-superuser CLI command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_help_text(self, runner):
        """Test that help text is displayed."""
        result = runner.invoke(cli, ["create-superuser", "--help"])
        assert result.exit_code == 0
        assert "Create a Django superuser" in result.output
        assert "--reference" in result.output
        assert "--settings" in result.output

    def test_no_reference_configured(self, runner, mocker, tmp_path):
        """Test error when no reference is provided or configured."""
        # Create an empty pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.epicenv]\n")

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code != 0
        assert "No 1Password reference provided" in result.output

    def test_django_not_installed(self, runner, mocker, tmp_path):
        """Test error when Django is not installed."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.epicenv.django]\nsuperuser_reference = "op://test/item"\n')

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )
        mocker.patch(
            "epicenv._django.check_django_available",
            return_value=(False, "Django is not installed"),
        )

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code != 0
        assert "Django" in result.output

    def test_onepassword_not_available(self, runner, mocker, tmp_path):
        """Test error when 1Password CLI is not available."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.epicenv.django]\nsuperuser_reference = "op://test/item"\n')

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )
        mocker.patch(
            "epicenv._django.check_django_available",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv._django.setup_django_environment",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv._django.check_database_ready",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv._django.check_user_table_exists",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code != 0
        assert "1Password" in result.output


class TestFetchSuperuserCredentials:
    """Tests for _fetch_superuser_credentials function."""

    def test_fetch_all_fields_success(self, mocker):
        """Test successful fetch of all credential fields."""
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_from_onepassword",
            side_effect=[
                ("admin", None),  # username
                ("admin@example.com", None),  # email
                ("secret123", None),  # password
            ],
        )

        credentials, error = _fetch_superuser_credentials("op://vault/item", {})

        assert credentials is not None
        assert credentials.username == "admin"
        assert credentials.email == "admin@example.com"
        assert credentials.password == "secret123"  # noqa: S105
        assert error is None

    def test_fetch_username_failure(self, mocker):
        """Test error when username fetch fails."""
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_from_onepassword",
            return_value=(None, "Field not found"),
        )

        credentials, error = _fetch_superuser_credentials("op://vault/item", {})

        assert credentials is None
        assert "username" in error.lower()

    def test_fetch_email_failure(self, mocker):
        """Test error when email fetch fails."""
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_from_onepassword",
            side_effect=[
                ("admin", None),  # username succeeds
                (None, "Field not found"),  # email fails
            ],
        )

        credentials, error = _fetch_superuser_credentials("op://vault/item", {})

        assert credentials is None
        assert "email" in error.lower()

    def test_fetch_password_failure(self, mocker):
        """Test error when password fetch fails."""
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_from_onepassword",
            side_effect=[
                ("admin", None),  # username succeeds
                ("admin@example.com", None),  # email succeeds
                (None, "Field not found"),  # password fails
            ],
        )

        credentials, error = _fetch_superuser_credentials("op://vault/item", {})

        assert credentials is None
        assert "password" in error.lower()

    def test_fetch_with_custom_field_names(self, mocker):
        """Test fetch with custom field name mappings."""
        mock_fetch = mocker.patch(
            "epicenv.cli.create_superuser._fetch_from_onepassword",
            side_effect=[
                ("admin", None),
                ("admin@example.com", None),
                ("secret123", None),
            ],
        )

        config = {
            "superuser_fields": {
                "username": "user",
                "email": "mail",
                "password": "pass",
            }
        }

        credentials, error = _fetch_superuser_credentials("op://vault/item", config)

        assert credentials is not None
        # Verify custom field names were used
        calls = mock_fetch.call_args_list
        assert "op://vault/item/user" in str(calls[0])
        assert "op://vault/item/mail" in str(calls[1])
        assert "op://vault/item/pass" in str(calls[2])


class TestCreateOrUpdateSuperuser:
    """Tests for _create_or_update_superuser function."""

    def test_create_new_user(self, mocker):
        """Test creating a new superuser when none exists."""
        mocker.patch(
            "epicenv._django.find_existing_user",
            return_value=None,
        )
        mock_user = MagicMock()
        mock_user.username = "admin"
        mocker.patch(
            "epicenv._django.create_superuser",
            return_value=(mock_user, None),
        )

        credentials = SuperuserCredentials(
            username="admin",
            email="admin@example.com",
            password="secret123",  # noqa: S106
        )
        success, message, was_created = _create_or_update_superuser(credentials, ["username"])

        assert success is True
        assert was_created is True
        assert "admin" in message

    def test_update_existing_user_by_username(self, mocker):
        """Test updating password when user exists (found by username)."""
        existing_user = MagicMock()
        existing_user.username = "admin"
        mocker.patch(
            "epicenv._django.find_existing_user",
            return_value=existing_user,
        )
        mocker.patch(
            "epicenv._django.update_user_password",
            return_value=(True, None),
        )

        credentials = SuperuserCredentials(
            username="admin",
            email="admin@example.com",
            password="newpassword",  # noqa: S106
        )
        success, message, was_created = _create_or_update_superuser(credentials, ["username"])

        assert success is True
        assert was_created is False
        assert "Updated" in message

    def test_update_existing_user_by_email(self, mocker):
        """Test updating password when user exists (found by email)."""
        existing_user = MagicMock()
        existing_user.username = "admin"
        mocker.patch(
            "epicenv._django.find_existing_user",
            return_value=existing_user,
        )
        mocker.patch(
            "epicenv._django.update_user_password",
            return_value=(True, None),
        )

        credentials = SuperuserCredentials(
            username="admin",
            email="admin@example.com",
            password="newpassword",  # noqa: S106
        )
        success, message, was_created = _create_or_update_superuser(credentials, ["email"])

        assert success is True
        assert was_created is False

    def test_create_user_failure(self, mocker):
        """Test error when creating user fails."""
        mocker.patch(
            "epicenv._django.find_existing_user",
            return_value=None,
        )
        mocker.patch(
            "epicenv._django.create_superuser",
            return_value=(None, "Database error"),
        )

        credentials = SuperuserCredentials(
            username="admin",
            email="admin@example.com",
            password="secret123",  # noqa: S106
        )
        success, message, was_created = _create_or_update_superuser(credentials, ["username"])

        assert success is False
        assert was_created is False

    def test_update_password_failure(self, mocker):
        """Test error when updating password fails."""
        existing_user = MagicMock()
        existing_user.username = "admin"
        mocker.patch(
            "epicenv._django.find_existing_user",
            return_value=existing_user,
        )
        mocker.patch(
            "epicenv._django.update_user_password",
            return_value=(False, "Password validation failed"),
        )

        credentials = SuperuserCredentials(
            username="admin",
            email="admin@example.com",
            password="weak",  # noqa: S106
        )
        success, message, was_created = _create_or_update_superuser(credentials, ["username"])

        assert success is False
        assert was_created is False


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_load_django_config(self, tmp_path):
        """Test loading django config from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.epicenv.django]
superuser_reference = "op://Dev/Admin"
superuser_lookup_fields = ["username", "email"]
"""
        )

        from epicenv._config import get_django_config

        config = get_django_config(pyproject)
        assert config["superuser_reference"] == "op://Dev/Admin"
        assert config["superuser_lookup_fields"] == ["username", "email"]

    def test_load_django_config_with_field_mappings(self, tmp_path):
        """Test loading django config with custom field mappings."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.epicenv.django]
superuser_reference = "op://Dev/Admin"

[tool.epicenv.django.superuser_fields]
username = "user"
email = "mail"
password = "pass"
"""
        )

        from epicenv._config import get_django_config

        config = get_django_config(pyproject)
        assert config["superuser_reference"] == "op://Dev/Admin"
        assert config["superuser_fields"]["username"] == "user"
        assert config["superuser_fields"]["email"] == "mail"
        assert config["superuser_fields"]["password"] == "pass"  # noqa: S105

    def test_empty_django_config(self, tmp_path):
        """Test when no django config exists."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.epicenv]\n")

        from epicenv._config import get_django_config

        config = get_django_config(pyproject)
        assert config == {}


class TestSuperuserCredentials:
    """Tests for SuperuserCredentials named tuple."""

    def test_credentials_creation(self):
        """Test creating SuperuserCredentials."""
        creds = SuperuserCredentials(
            username="admin",
            email="admin@example.com",
            password="secret123",  # noqa: S106
        )

        assert creds.username == "admin"
        assert creds.email == "admin@example.com"
        assert creds.password == "secret123"  # noqa: S105

    def test_credentials_immutability(self):
        """Test that SuperuserCredentials is immutable."""
        creds = SuperuserCredentials(
            username="admin",
            email="admin@example.com",
            password="secret123",  # noqa: S106
        )

        with pytest.raises(AttributeError):
            creds.username = "other"
