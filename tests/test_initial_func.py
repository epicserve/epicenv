"""Tests for initial_func functionality with args and kwargs."""

from epicenv._env import get_callable, get_dot_env_file_str
from epicenv.initializers import url_safe_password


class TestGetCallable:
    """Test the get_callable function with various argument configurations."""

    def test_get_callable_without_args(self):
        """Test get_callable with no arguments."""
        func = get_callable("epicenv.initializers.url_safe_password")
        result = func()

        # Default length is 50
        assert isinstance(result, str)
        assert len(result) == 50
        # Should only contain URL-safe characters
        assert all(c.isalnum() or c in "-_" for c in result)

    def test_get_callable_with_args(self):
        """Test get_callable with positional arguments."""
        func = get_callable("epicenv.initializers.url_safe_password", args=[32])
        result = func()

        assert isinstance(result, str)
        assert len(result) == 32
        assert all(c.isalnum() or c in "-_" for c in result)

    def test_get_callable_with_kwargs(self):
        """Test get_callable with keyword arguments."""
        func = get_callable("epicenv.initializers.url_safe_password", kwargs={"length": 64})
        result = func()

        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c.isalnum() or c in "-_" for c in result)

    def test_get_callable_with_mixed_args_kwargs(self):
        """Test get_callable with both positional and keyword arguments."""
        # Using a test function that accepts both args and kwargs
        func = get_callable("epicenv.initializers.url_safe_password", kwargs={"length": 100})
        result = func()

        assert isinstance(result, str)
        assert len(result) == 100

    def test_get_callable_returns_different_values(self):
        """Test that calling get_callable multiple times generates different values."""
        func = get_callable("epicenv.initializers.url_safe_password", args=[20])
        result1 = func()
        result2 = func()

        # Should generate different random values each time
        assert result1 != result2
        assert len(result1) == 20
        assert len(result2) == 20


class TestUrlSafePassword:
    """Test the initializers.url_safe_password function."""

    def test_url_safe_password_default_length(self):
        """Test url_safe_password with default length."""
        password = url_safe_password()
        assert isinstance(password, str)
        assert len(password) == 50

    def test_url_safe_password_custom_length(self):
        """Test url_safe_password with custom length."""
        for length in [10, 25, 50, 100, 200]:
            password = url_safe_password(length=length)
            assert len(password) == length
            assert all(c.isalnum() or c in "-_" for c in password)

    def test_url_safe_password_randomness(self):
        """Test that url_safe_password generates different passwords."""
        passwords = [url_safe_password() for _ in range(10)]
        # All passwords should be unique
        assert len(set(passwords)) == 10

    def test_url_safe_password_character_distribution(self):
        """Test that url_safe_password uses all types of allowed characters."""
        # Generate a long password to ensure we get variety
        password = url_safe_password(length=1000)

        has_lowercase = any(c.islower() for c in password)
        has_uppercase = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)

        # With 1000 characters, we should have all types
        assert has_lowercase
        assert has_uppercase
        assert has_digit


class TestOnePasswordIntegration:
    """Test integration of onepassword initializer with get_callable."""

    def test_get_callable_with_onepassword_success(self, mocker):
        """Test onepassword via get_callable when 1Password is available."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(True, None),
        )
        mocker.patch(
            "epicenv.initializers._onepassword._fetch_from_onepassword",
            return_value=("secret123", None),
        )

        func = get_callable(
            "epicenv.initializers.onepassword",
            args=["op://vault/item/field"],
            kwargs={"_variable_name": "API_KEY"},
        )
        result = func()

        assert result == "secret123"

    def test_get_callable_with_onepassword_fallback(self, mocker):
        """Test onepassword via get_callable uses fallback when unavailable."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        func = get_callable(
            "epicenv.initializers.onepassword",
            args=["op://vault/item/field"],
            kwargs={"_variable_name": "STRIPE_KEY", "silent": True},
        )
        result = func()

        assert result == "[Enter STRIPE_KEY]"

    def test_get_callable_with_onepassword_custom_fallback(self, mocker):
        """Test onepassword via get_callable with custom fallback."""
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "1Password CLI not installed"),
        )

        func = get_callable(
            "epicenv.initializers.onepassword",
            args=["op://vault/item/field"],
            kwargs={"fallback": "my_custom_value", "silent": True},
        )
        result = func()

        assert result == "my_custom_value"

    def test_get_dot_env_file_str_injects_variable_name(self, mocker, tmp_path):
        """Test that get_dot_env_file_str automatically injects _variable_name."""
        # Create a temporary pyproject.toml with onepassword initializer
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[tool.epicenv.variables.TEST_SECRET]
type = "str"
required = true
help_text = "Test secret from 1Password"
initial_func = "epicenv.initializers.onepassword"
args = ["op://vault/item/field"]
"""
        )

        # Mock 1Password to return a test value
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(True, None),
        )

        def mock_fetch(reference):
            # This will be called by onepassword()
            return ("test_value", None)

        mocker.patch(
            "epicenv.initializers._onepassword._fetch_from_onepassword",
            side_effect=mock_fetch,
        )

        # Mock find_pyproject_toml to return our test file
        # Need to mock where it's imported, not where it's defined
        mocker.patch(
            "epicenv._env.find_pyproject_toml",
            return_value=pyproject_file,
        )

        # Generate the .env file
        result = get_dot_env_file_str()

        # Verify the secret was fetched successfully
        assert "TEST_SECRET=test_value" in result

    def test_get_dot_env_file_str_with_onepassword_fallback(self, mocker, tmp_path, capsys):
        """Test .env generation with 1Password fallback."""
        # Create a temporary pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[tool.epicenv.variables.API_KEY]
type = "str"
required = true
help_text = "API key from 1Password"
initial_func = "epicenv.initializers.onepassword"
args = ["op://Production/API/key"]

[tool.epicenv.variables.DATABASE_PASSWORD]
type = "str"
required = true
initial_func = "epicenv.initializers.onepassword"
args = ["op://Production/Database/password"]

[tool.epicenv.variables.DATABASE_PASSWORD.kwargs]
fallback = "dev_password"
"""
        )

        # Mock 1Password as unavailable
        mocker.patch(
            "epicenv.initializers._onepassword._check_onepassword_available",
            return_value=(False, "Not signed in to 1Password CLI"),
        )

        # Mock find_pyproject_toml to return our test file
        # Need to mock where it's imported, not where it's defined
        mocker.patch(
            "epicenv._env.find_pyproject_toml",
            return_value=pyproject_file,
        )

        # Generate the .env file
        result = get_dot_env_file_str()

        # Verify fallback values are used
        assert "API_KEY=[Enter API_KEY]" in result
        assert "DATABASE_PASSWORD=dev_password" in result

        # Verify warnings were shown
        captured = capsys.readouterr()
        assert "1Password CLI not available for API_KEY" in captured.err
        assert "1Password CLI not available for DATABASE_PASSWORD" in captured.err
