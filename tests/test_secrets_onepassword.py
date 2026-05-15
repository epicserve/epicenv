"""Tests for the secrets.onepassword module."""

import subprocess
from unittest.mock import Mock

from epicenv.secrets.onepassword import (
    OnePasswordProvider,
    check_available,
    fetch_field,
    fetch_fields,
)


class TestCheckAvailable:
    def test_available_and_signed_in(self, mocker):
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="2.0.0", stderr=""),
                Mock(returncode=0, stdout="user@example.com", stderr=""),
            ],
        )
        is_available, error = check_available()
        assert is_available is True
        assert error is None

    def test_cli_not_installed_returncode(self, mocker):
        mocker.patch("subprocess.run", return_value=Mock(returncode=1, stdout="", stderr=""))
        is_available, error = check_available()
        assert is_available is False
        assert error == "1Password CLI not installed"

    def test_cli_not_installed_filenotfound(self, mocker):
        mocker.patch("subprocess.run", side_effect=FileNotFoundError("op: command not found"))
        is_available, error = check_available()
        assert is_available is False
        assert error == "1Password CLI not installed"

    def test_not_signed_in(self, mocker):
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="2.0.0", stderr=""),
                Mock(returncode=1, stdout="", stderr="not signed in"),
            ],
        )
        is_available, error = check_available()
        assert is_available is False
        assert error == "Not signed in to 1Password CLI"

    def test_version_timeout(self, mocker):
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("op", 5))
        is_available, error = check_available()
        assert is_available is False
        assert error == "1Password CLI not responding"

    def test_whoami_timeout(self, mocker):
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="2.0.0", stderr=""),
                subprocess.TimeoutExpired("op", 5),
            ],
        )
        is_available, error = check_available()
        assert is_available is False
        assert error == "1Password CLI not responding"

    def test_oserror_on_version(self, mocker):
        mocker.patch("subprocess.run", side_effect=OSError("Permission denied"))
        is_available, error = check_available()
        assert is_available is False
        assert "Permission denied" in error

    def test_oserror_on_whoami(self, mocker):
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="2.0.0", stderr=""),
                OSError("Broken pipe"),
            ],
        )
        is_available, error = check_available()
        assert is_available is False
        assert "Broken pipe" in error


class TestFetchField:
    def test_success(self, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="super_secret_value\n", stderr=""),
        )
        value, error = fetch_field("op://vault/item/field")
        assert value == "super_secret_value"
        assert error is None

    def test_failure_with_stderr(self, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=Mock(returncode=1, stdout="", stderr="[ERROR] vault not found"),
        )
        value, error = fetch_field("op://vault/item/field")
        assert value is None
        assert "Failed to read secret" in error
        assert "vault not found" in error

    def test_failure_without_stderr(self, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=Mock(returncode=1, stdout="", stderr=""),
        )
        value, error = fetch_field("op://vault/item/field")
        assert value is None
        assert "Unknown error" in error

    def test_timeout(self, mocker):
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("op", 10))
        value, error = fetch_field("op://vault/item/field")
        assert value is None
        assert error == "Timeout reading from 1Password"

    def test_unexpected_exception(self, mocker):
        mocker.patch("subprocess.run", side_effect=RuntimeError("Something went wrong"))
        value, error = fetch_field("op://vault/item/field")
        assert value is None
        assert "Unexpected error" in error
        assert "Something went wrong" in error

    def test_custom_timeout_passed_through(self, mocker):
        run = mocker.patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="ok", stderr=""),
        )
        fetch_field("op://vault/item/field", timeout=42)
        assert run.call_args.kwargs["timeout"] == 42


class TestFetchFields:
    def test_single_field(self, mocker):
        mocker.patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="value1", stderr=""),
        )
        values, error = fetch_fields("op://vault/item", ["password"])
        assert error is None
        assert values == {"password": "value1"}

    def test_multiple_fields(self, mocker):
        run = mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="admin", stderr=""),
                Mock(returncode=0, stdout="admin@example.com", stderr=""),
                Mock(returncode=0, stdout="secret", stderr=""),
            ],
        )
        values, error = fetch_fields("op://vault/item", ["username", "email", "password"])
        assert error is None
        assert values == {"username": "admin", "email": "admin@example.com", "password": "secret"}
        # Verify references were constructed correctly
        refs = [call.args[0][2] for call in run.call_args_list]
        assert refs == [
            "op://vault/item/username",
            "op://vault/item/email",
            "op://vault/item/password",
        ]

    def test_strips_trailing_slash(self, mocker):
        run = mocker.patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="val", stderr=""),
        )
        fetch_fields("op://vault/item/", ["password"])
        assert run.call_args.args[0][2] == "op://vault/item/password"

    def test_partial_failure_returns_error(self, mocker):
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="admin", stderr=""),
                Mock(returncode=1, stdout="", stderr="field not found"),
            ],
        )
        values, error = fetch_fields("op://vault/item", ["username", "missing"])
        assert values is None
        assert "missing" in error
        assert "field not found" in error

    def test_empty_field_list(self, mocker):
        mocker.patch("subprocess.run")
        values, error = fetch_fields("op://vault/item", [])
        assert error is None
        assert values == {}


class TestOnePasswordProvider:
    def test_is_available_delegates(self, mocker):
        mocker.patch(
            "epicenv.secrets.onepassword.check_available",
            return_value=(True, None),
        )
        provider = OnePasswordProvider()
        assert provider.is_available() == (True, None)

    def test_get_field_delegates(self, mocker):
        mocker.patch(
            "epicenv.secrets.onepassword.fetch_field",
            return_value=("secret", None),
        )
        provider = OnePasswordProvider()
        assert provider.get_field("op://vault/item/field") == ("secret", None)

    def test_get_fields_delegates(self, mocker):
        mocker.patch(
            "epicenv.secrets.onepassword.fetch_fields",
            return_value=({"username": "admin"}, None),
        )
        provider = OnePasswordProvider()
        assert provider.get_fields("op://vault/item", ["username"]) == ({"username": "admin"}, None)
