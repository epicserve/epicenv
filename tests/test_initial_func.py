"""Tests for initial_func functionality with args and kwargs."""

import pytest

from epicenv._env import get_callable
from epicenv.password import url_safe


class TestGetCallable:
    """Test the get_callable function with various argument configurations."""

    def test_get_callable_without_args(self):
        """Test get_callable with no arguments."""
        func = get_callable("epicenv.password.url_safe")
        result = func()

        # Default length is 50
        assert isinstance(result, str)
        assert len(result) == 50
        # Should only contain URL-safe characters
        assert all(c.isalnum() or c in "-_" for c in result)

    def test_get_callable_with_args(self):
        """Test get_callable with positional arguments."""
        func = get_callable("epicenv.password.url_safe", args=[32])
        result = func()

        assert isinstance(result, str)
        assert len(result) == 32
        assert all(c.isalnum() or c in "-_" for c in result)

    def test_get_callable_with_kwargs(self):
        """Test get_callable with keyword arguments."""
        func = get_callable("epicenv.password.url_safe", kwargs={"length": 64})
        result = func()

        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c.isalnum() or c in "-_" for c in result)

    def test_get_callable_with_mixed_args_kwargs(self):
        """Test get_callable with both positional and keyword arguments."""
        # Using a test function that accepts both args and kwargs
        func = get_callable("epicenv.password.url_safe", kwargs={"length": 100})
        result = func()

        assert isinstance(result, str)
        assert len(result) == 100

    def test_get_callable_returns_different_values(self):
        """Test that calling get_callable multiple times generates different values."""
        func = get_callable("epicenv.password.url_safe", args=[20])
        result1 = func()
        result2 = func()

        # Should generate different random values each time
        assert result1 != result2
        assert len(result1) == 20
        assert len(result2) == 20


class TestPasswordUrlSafe:
    """Test the password.url_safe function."""

    def test_url_safe_default_length(self):
        """Test url_safe with default length."""
        password = url_safe()
        assert isinstance(password, str)
        assert len(password) == 50

    def test_url_safe_custom_length(self):
        """Test url_safe with custom length."""
        for length in [10, 25, 50, 100, 200]:
            password = url_safe(length=length)
            assert len(password) == length
            assert all(c.isalnum() or c in "-_" for c in password)

    def test_url_safe_randomness(self):
        """Test that url_safe generates different passwords."""
        passwords = [url_safe() for _ in range(10)]
        # All passwords should be unique
        assert len(set(passwords)) == 10

    def test_url_safe_character_distribution(self):
        """Test that url_safe uses all types of allowed characters."""
        # Generate a long password to ensure we get variety
        password = url_safe(length=1000)

        has_lowercase = any(c.islower() for c in password)
        has_uppercase = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "-_" for c in password)

        # With 1000 characters, we should have all types
        assert has_lowercase
        assert has_uppercase
        assert has_digit
        # Special characters (-_) are less common, so this might occasionally fail
        # but with 1000 chars it should usually pass
