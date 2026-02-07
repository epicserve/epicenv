"""Tests for the create-superuser CLI command."""

import subprocess
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from epicenv.cli.create_superuser import (
    UserCredentials,
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
        assert "Create" in result.output
        assert "Django superuser" in result.output
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

    def test_onepassword_not_available(self, runner, mocker, tmp_path):
        """Test error when 1Password CLI is not available."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.epicenv.django]\nsuperuser_reference = "op://test/item"\n')

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )

        # Mock 1Password check to fail
        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code != 0
        assert "1Password" in result.output

    def test_django_settings_module_not_set(self, runner, mocker, tmp_path):
        """Test error when DJANGO_SETTINGS_MODULE is not set."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.epicenv.django]\nsuperuser_reference = "op://test/item"\n')

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )

        # Mock 1Password check to pass
        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(True, None),
        )

        # Mock credentials fetch
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_superuser_credentials",
            return_value=(UserCredentials("admin", "admin@example.com", "secret"), None),
        )

        # No need to mock load_variables - we use os.environ directly

        # Ensure DJANGO_SETTINGS_MODULE is not in env
        mocker.patch.dict("os.environ", {}, clear=True)

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code != 0
        assert "DJANGO_SETTINGS_MODULE" in result.output

    def test_successful_create_superuser(self, runner, mocker, tmp_path):
        """Test successful superuser creation via subprocess."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.epicenv.django]\nsuperuser_reference = "op://test/item"\n')

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )

        # Mock 1Password check to pass
        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(True, None),
        )

        # Mock credentials fetch
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_superuser_credentials",
            return_value=(UserCredentials("admin", "admin@example.com", "secret"), None),
        )

        # Mock os.environ to have DJANGO_SETTINGS_MODULE set
        mocker.patch.dict("os.environ", {"DJANGO_SETTINGS_MODULE": "myproject.settings"})

        # Mock subprocess.run to simulate successful creation
        mock_result = MagicMock()
        mock_result.stdout = "CREATED:admin"
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code == 0
        assert "Success!" in result.output
        assert "Created superuser: admin" in result.output

    def test_successful_update_superuser(self, runner, mocker, tmp_path):
        """Test successful superuser password update via subprocess."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.epicenv.django]\nsuperuser_reference = "op://test/item"\n')

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )

        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(True, None),
        )

        mocker.patch(
            "epicenv.cli.create_superuser._fetch_superuser_credentials",
            return_value=(UserCredentials("admin", "admin@example.com", "secret"), None),
        )

        mocker.patch.dict("os.environ", {"DJANGO_SETTINGS_MODULE": "myproject.settings"})

        # Mock subprocess.run to simulate successful update
        mock_result = MagicMock()
        mock_result.stdout = "UPDATED:admin"
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code == 0
        assert "Success!" in result.output
        assert "Updated password for existing user: admin" in result.output

    def test_subprocess_failure(self, runner, mocker, tmp_path):
        """Test handling of subprocess failure."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.epicenv.django]\nsuperuser_reference = "op://test/item"\n')

        mocker.patch(
            "epicenv.cli.create_superuser.find_pyproject_toml",
            return_value=pyproject,
        )

        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(True, None),
        )

        mocker.patch(
            "epicenv.cli.create_superuser._fetch_superuser_credentials",
            return_value=(UserCredentials("admin", "admin@example.com", "secret"), None),
        )

        mocker.patch.dict("os.environ", {"DJANGO_SETTINGS_MODULE": "myproject.settings"})

        # Mock subprocess.run to raise CalledProcessError
        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "python", stderr="Database connection failed"),
        )

        result = runner.invoke(cli, ["create-superuser"])
        assert result.exit_code != 0
        assert "Error:" in result.output


class TestFetchUserCredentials:
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


class TestUserCredentials:
    """Tests for UserCredentials named tuple."""

    def test_credentials_creation(self):
        """Test creating UserCredentials."""
        creds = UserCredentials(
            username="admin",
            email="admin@example.com",
            password="secret123",  # noqa: S106
        )

        assert creds.username == "admin"
        assert creds.email == "admin@example.com"
        assert creds.password == "secret123"  # noqa: S105

    def test_credentials_immutability(self):
        """Test that UserCredentials is immutable."""
        creds = UserCredentials(
            username="admin",
            email="admin@example.com",
            password="secret123",  # noqa: S106
        )

        with pytest.raises(AttributeError):
            creds.username = "other"


class TestSubprocessIntegration:
    """Tests for subprocess execution."""

    def test_subprocess_called_with_correct_args(self, mocker):
        """Test that subprocess is called with correct arguments."""
        from epicenv.cli.create_superuser import create_superuser

        mocker.patch("epicenv.cli.create_superuser.find_pyproject_toml", return_value=None)
        mocker.patch(
            "epicenv.cli.create_superuser.get_django_config",
            return_value={"superuser_reference": "op://vault/item"},
        )
        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_superuser_credentials",
            return_value=(UserCredentials("admin", "admin@example.com", "secret"), None),
        )

        # Mock os.environ to have DJANGO_SETTINGS_MODULE
        mocker.patch.dict("os.environ", {"DJANGO_SETTINGS_MODULE": "myproject.settings"})

        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.stdout = "CREATED:admin"
        mock_result.returncode = 0
        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        create_superuser(reference="op://vault/item")

        # Verify subprocess.run was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # Check that credentials were passed as arguments
        assert "admin" in call_args[0][0]  # username in command
        assert "admin@example.com" in call_args[0][0]  # email in command
        assert "secret" in call_args[0][0]  # password in command

        # Check that environment was passed
        assert "env" in call_args[1]
        assert call_args[1]["env"]["DJANGO_SETTINGS_MODULE"] == "myproject.settings"

    def test_subprocess_with_custom_lookup_fields(self, mocker, tmp_path):
        """Test subprocess call with custom lookup fields."""
        from epicenv.cli.create_superuser import create_superuser

        # Create a dummy pyproject path so config is loaded
        pyproject = tmp_path / "pyproject.toml"
        mocker.patch("epicenv.cli.create_superuser.find_pyproject_toml", return_value=pyproject)
        mocker.patch(
            "epicenv.cli.create_superuser.get_django_config",
            return_value={
                "superuser_reference": "op://vault/item",
                "superuser_lookup_fields": ["username", "email"],
            },
        )
        mocker.patch(
            "epicenv.cli.create_superuser._check_onepassword_available",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv.cli.create_superuser._fetch_superuser_credentials",
            return_value=(UserCredentials("admin", "admin@example.com", "secret"), None),
        )
        mocker.patch.dict("os.environ", {"DJANGO_SETTINGS_MODULE": "myproject.settings"})

        mock_result = MagicMock()
        mock_result.stdout = "CREATED:admin"
        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        create_superuser(reference="op://vault/item")

        # Verify lookup fields were passed
        call_args = mock_run.call_args
        # The lookup fields should be in the arguments list (after username, email, password)
        # call_args[0][0] is a list like:
        # [python_path, '-c', script, 'admin', 'admin@example.com', 'secret', 'username, email']
        assert len(call_args[0][0]) >= 7, "Subprocess should have 7+ arguments"
        assert call_args[0][0][6] == "username,email", "Lookup fields should be 'username,email'"
