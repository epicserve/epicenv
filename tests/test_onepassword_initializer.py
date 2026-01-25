"""Tests for the onepassword initializer function."""

import subprocess
from unittest.mock import Mock

from epicenv.initializers import (
    _check_onepassword_available,
    _fetch_from_onepassword,
    _generate_fallback_placeholder,
    onepassword,
)


class TestCheckOnePasswordAvailable:
    """Tests for _check_onepassword_available helper function."""

    def test_onepassword_available_and_signed_in(self, mocker):
        """Test when 1Password CLI is installed and user is signed in."""
        # Mock successful --version check
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="2.0.0", stderr=""),  # --version
                Mock(returncode=0, stdout="user@example.com", stderr=""),  # whoami
            ],
        )

        is_available, error = _check_onepassword_available()

        assert is_available is True
        assert error is None

    def test_onepassword_cli_not_installed(self, mocker):
        """Test when 1Password CLI is not installed."""
        mocker.patch(
            "subprocess.run",
            side_effect=FileNotFoundError("op: command not found"),
        )

        is_available, error = _check_onepassword_available()

        assert is_available is False
        assert error == "1Password CLI not installed"

    def test_onepassword_not_signed_in(self, mocker):
        """Test when 1Password CLI is installed but user not signed in."""
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="2.0.0", stderr=""),  # --version
                Mock(returncode=1, stdout="", stderr="not signed in"),  # whoami
            ],
        )

        is_available, error = _check_onepassword_available()

        assert is_available is False
        assert error == "Not signed in to 1Password CLI"

    def test_onepassword_version_timeout(self, mocker):
        """Test when --version command times out."""
        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("op", 5),
        )

        is_available, error = _check_onepassword_available()

        assert is_available is False
        assert error == "1Password CLI not responding"

    def test_onepassword_whoami_timeout(self, mocker):
        """Test when whoami command times out."""
        mocker.patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="2.0.0", stderr=""),  # --version
                subprocess.TimeoutExpired("op", 5),  # whoami timeout
            ],
        )

        is_available, error = _check_onepassword_available()

        assert is_available is False
        assert error == "1Password CLI not responding"


class TestFetchFromOnePassword:
    """Tests for _fetch_from_onepassword helper function."""

    def test_fetch_success(self, mocker):
        """Test successful secret fetch."""
        mocker.patch(
            "subprocess.run",
            return_value=Mock(
                returncode=0,
                stdout="super_secret_value\n",
                stderr="",
            ),
        )

        value, error = _fetch_from_onepassword("op://vault/item/field")

        assert value == "super_secret_value"
        assert error is None

    def test_fetch_failure_with_error_message(self, mocker):
        """Test fetch failure with error message from op CLI."""
        mocker.patch(
            "subprocess.run",
            return_value=Mock(
                returncode=1,
                stdout="",
                stderr="[ERROR] vault not found",
            ),
        )

        value, error = _fetch_from_onepassword("op://vault/item/field")

        assert value is None
        assert "Failed to read secret" in error
        assert "vault not found" in error

    def test_fetch_timeout(self, mocker):
        """Test fetch timeout."""
        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("op", 10),
        )

        value, error = _fetch_from_onepassword("op://vault/item/field")

        assert value is None
        assert error == "Timeout reading from 1Password"

    def test_fetch_unexpected_exception(self, mocker):
        """Test handling of unexpected exceptions."""
        mocker.patch(
            "subprocess.run",
            side_effect=Exception("Unexpected error occurred"),
        )

        value, error = _fetch_from_onepassword("op://vault/item/field")

        assert value is None
        assert "Unexpected error" in error
        assert "Unexpected error occurred" in error


class TestGenerateFallbackPlaceholder:
    """Tests for _generate_fallback_placeholder helper function."""

    def test_with_variable_name(self):
        """Test placeholder generation with variable name."""
        result = _generate_fallback_placeholder("STRIPE_API_KEY")
        assert result == "[Enter STRIPE_API_KEY]"

    def test_with_different_variable_name(self):
        """Test placeholder generation with different variable name."""
        result = _generate_fallback_placeholder("DATABASE_PASSWORD")
        assert result == "[Enter DATABASE_PASSWORD]"

    def test_without_variable_name(self):
        """Test placeholder generation without variable name."""
        result = _generate_fallback_placeholder(None)
        assert result == "[Enter 1Password credential]"


class TestOnePasswordInitializer:
    """Tests for the main onepassword() function."""

    def test_onepassword_success(self, mocker):
        """Test successful fetch from 1Password."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv.initializers._onepassword._fetch_from_onepassword",
            return_value=("secret123", None),
        )

        result = onepassword(
            reference="op://vault/item/field",
            _variable_name="API_KEY",
        )

        assert result == "secret123"

    def test_onepassword_cli_not_installed_uses_auto_fallback(self, mocker, capsys):
        """Test fallback when 1Password CLI not installed."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        result = onepassword(
            reference="op://vault/item/field",
            _variable_name="STRIPE_API_KEY",
        )

        assert result == "[Enter STRIPE_API_KEY]"

        # Check that warning was printed to stderr
        captured = capsys.readouterr()
        assert "1Password CLI not available for STRIPE_API_KEY" in captured.err
        assert "op://vault/item/field" in captured.err
        assert "[Enter STRIPE_API_KEY]" in captured.err

    def test_onepassword_with_custom_fallback(self, mocker, capsys):
        """Test that custom fallback is used."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        result = onepassword(
            reference="op://vault/item/field",
            fallback="my_custom_fallback",
            _variable_name="API_KEY",
        )

        assert result == "my_custom_fallback"

        # Check that warning shows custom fallback
        captured = capsys.readouterr()
        assert "my_custom_fallback" in captured.err

    def test_onepassword_auto_fallback_with_variable_name(self, mocker, capsys):
        """Test auto fallback uses variable name."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "Not signed in to 1Password CLI"),
        )

        result = onepassword(
            reference="op://vault/item/field",
            _variable_name="DATABASE_PASSWORD",
        )

        assert result == "[Enter DATABASE_PASSWORD]"

    def test_onepassword_auto_fallback_without_variable_name(self, mocker, capsys):
        """Test auto fallback without variable name uses generic placeholder."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        result = onepassword(
            reference="op://vault/item/field",
            _variable_name=None,
        )

        assert result == "[Enter 1Password credential]"

    def test_onepassword_silent_mode(self, mocker, capsys):
        """Test that silent mode suppresses warnings."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        result = onepassword(
            reference="op://vault/item/field",
            silent=True,
            _variable_name="API_KEY",
        )

        assert result == "[Enter API_KEY]"

        # Check that no warning was printed
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_onepassword_fetch_error_uses_fallback(self, mocker, capsys):
        """Test that fetch errors result in fallback."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv.initializers._onepassword._fetch_from_onepassword",
            return_value=(None, "Failed to read secret: vault not found"),
        )

        result = onepassword(
            reference="op://vault/item/field",
            _variable_name="SECRET_KEY",
        )

        assert result == "[Enter SECRET_KEY]"

        # Check that error message is shown
        captured = capsys.readouterr()
        assert "vault not found" in captured.err

    def test_onepassword_timeout_uses_fallback(self, mocker, capsys):
        """Test that timeouts result in fallback."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv.initializers._onepassword._fetch_from_onepassword",
            return_value=(None, "Timeout reading from 1Password"),
        )

        result = onepassword(
            reference="op://vault/item/field",
            _variable_name="API_TOKEN",
        )

        assert result == "[Enter API_TOKEN]"

        # Check that timeout message is shown
        captured = capsys.readouterr()
        assert "Timeout" in captured.err

    def test_onepassword_reference_preserved_in_warning(self, mocker, capsys):
        """Test that the reference is shown in warning messages."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "Not signed in to 1Password CLI"),
        )

        reference = "op://Production/API Keys/stripe_key"
        onepassword(reference=reference, _variable_name="STRIPE_KEY")

        captured = capsys.readouterr()
        assert reference in captured.err
        assert "op signin" in captured.err
        assert "epicenv create --overwrite" in captured.err
