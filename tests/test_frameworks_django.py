"""Tests for the frameworks.django integration module."""

import pytest

from epicenv.frameworks.django import DjangoSuperuserIntegration


@pytest.fixture
def integration(mocker):
    """Return a DjangoSuperuserIntegration with the DB-touching helpers stubbed."""
    user_exists = mocker.patch("epicenv.frameworks.django.user_exists", return_value=False)
    create = mocker.patch("epicenv.frameworks.django.create_superuser_record")
    update = mocker.patch("epicenv.frameworks.django.update_superuser_record")
    inst = DjangoSuperuserIntegration()
    inst._user_exists = user_exists
    inst._create = create
    inst._update = update
    return inst


class TestIsAvailable:
    def test_django_installed(self):
        # Django is in dev deps, so the import succeeds in the test env
        available, error = DjangoSuperuserIntegration().is_available()
        assert available is True
        assert error is None

    def test_django_missing(self, mocker):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "django":
                raise ImportError("No module named 'django'")
            return real_import(name, *args, **kwargs)

        mocker.patch("builtins.__import__", side_effect=fake_import)
        available, error = DjangoSuperuserIntegration().is_available()
        assert available is False
        assert "Django is not installed" in error


class TestExecute:
    def test_creates_new_user(self, integration):
        integration._user_exists.return_value = False
        result = integration.execute(
            username="admin", email="a@b.c", password="secret", database="default", force=False
        )
        assert result == "created"
        integration._create.assert_called_once_with("admin", "a@b.c", "secret", "default")
        integration._update.assert_not_called()

    def test_skips_existing_user_without_force(self, integration):
        integration._user_exists.return_value = True
        result = integration.execute(
            username="admin", email="a@b.c", password="secret", database="default", force=False
        )
        assert result == "exists"
        integration._create.assert_not_called()
        integration._update.assert_not_called()

    def test_updates_existing_user_with_force(self, integration):
        integration._user_exists.return_value = True
        result = integration.execute(
            username="admin", email="new@example.com", password="newpass", database="default", force=True
        )
        assert result == "updated"
        integration._update.assert_called_once_with("admin", "new@example.com", "newpass", "default")
        integration._create.assert_not_called()

    def test_passes_database_alias_through(self, integration):
        integration._user_exists.return_value = False
        integration.execute(
            username="admin", email="a@b.c", password="secret", database="replica", force=False
        )
        integration._user_exists.assert_called_once_with("admin", "replica")
        integration._create.assert_called_once_with("admin", "a@b.c", "secret", "replica")

    def test_create_failure_propagates(self, integration):
        integration._user_exists.return_value = False
        integration._create.side_effect = RuntimeError("constraint violation")
        with pytest.raises(RuntimeError, match="constraint violation"):
            integration.execute(
                username="admin", email="a@b.c", password="secret", database="default", force=False
            )
