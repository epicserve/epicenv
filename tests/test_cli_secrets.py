"""Tests for the `epicenv secrets get` CLI command."""

import json

from click.testing import CliRunner

from epicenv.cli.main import cli


def _patch_provider(mocker, *, available=(True, None), field=None, fields=None):
    """Patch OnePasswordProvider used by the CLI with stubbed return values."""
    instance = mocker.MagicMock()
    instance.is_available.return_value = available
    if field is not None:
        instance.get_field.return_value = field
    if fields is not None:
        instance.get_fields.return_value = fields
    mocker.patch("epicenv.cli.secrets.OnePasswordProvider", return_value=instance)
    return instance


class TestSecretsGetSingleField:
    def test_json_format_single_field(self, mocker):
        _patch_provider(mocker, field=("super_secret", None))
        result = CliRunner().invoke(cli, ["secrets", "get", "op://vault/item/password"])
        assert result.exit_code == 0
        assert json.loads(result.output.strip()) == {"value": "super_secret"}

    def test_plain_format_single_field(self, mocker):
        _patch_provider(mocker, field=("super_secret", None))
        result = CliRunner().invoke(cli, ["secrets", "get", "op://vault/item/password", "--format", "plain"])
        assert result.exit_code == 0
        assert result.output.strip() == "super_secret"

    def test_get_field_error_exits_non_zero(self, mocker):
        _patch_provider(mocker, field=(None, "Failed to read secret: not found"))
        result = CliRunner().invoke(cli, ["secrets", "get", "op://vault/item/missing"])
        assert result.exit_code == 1
        assert "Failed to read secret" in result.output


class TestSecretsGetMultipleFields:
    def test_json_format_multiple_fields(self, mocker):
        _patch_provider(
            mocker,
            fields=({"username": "admin", "email": "a@b.c", "password": "secret"}, None),
        )
        result = CliRunner().invoke(
            cli,
            ["secrets", "get", "op://vault/item", "--fields", "username,email,password"],
        )
        assert result.exit_code == 0
        assert json.loads(result.output.strip()) == {
            "username": "admin",
            "email": "a@b.c",
            "password": "secret",
        }

    def test_env_format(self, mocker):
        _patch_provider(
            mocker,
            fields=({"username": "admin", "password": "secret"}, None),
        )
        result = CliRunner().invoke(
            cli,
            ["secrets", "get", "op://vault/item", "--fields", "username,password", "--format", "env"],
        )
        assert result.exit_code == 0
        lines = result.output.strip().splitlines()
        assert "USERNAME=admin" in lines
        assert "PASSWORD=secret" in lines

    def test_plain_format_rejects_multiple_fields(self, mocker):
        _patch_provider(
            mocker,
            fields=({"a": "1", "b": "2"}, None),
        )
        result = CliRunner().invoke(
            cli,
            ["secrets", "get", "op://vault/item", "--fields", "a,b", "--format", "plain"],
        )
        assert result.exit_code == 1
        assert "Plain format only supports single field" in result.output

    def test_fields_are_stripped_of_whitespace(self, mocker):
        provider = _patch_provider(
            mocker,
            fields=({"username": "admin", "password": "secret"}, None),
        )
        CliRunner().invoke(
            cli,
            ["secrets", "get", "op://vault/item", "--fields", " username , password "],
        )
        provider.get_fields.assert_called_once_with("op://vault/item", ["username", "password"])

    def test_get_fields_error_exits_non_zero(self, mocker):
        _patch_provider(mocker, fields=(None, "Failed to fetch field 'missing': field not found"))
        result = CliRunner().invoke(
            cli,
            ["secrets", "get", "op://vault/item", "--fields", "missing"],
        )
        assert result.exit_code == 1
        assert "field not found" in result.output


class TestSecretsGetAvailabilityErrors:
    def test_not_installed_prints_setup_instructions(self, mocker):
        _patch_provider(mocker, field=(None, "1Password CLI not installed"))
        result = CliRunner().invoke(cli, ["secrets", "get", "op://vault/item/field"])
        assert result.exit_code == 1
        assert "1Password CLI not installed" in result.output
        assert "op signin" in result.output

    def test_not_signed_in_prints_setup_instructions(self, mocker):
        _patch_provider(
            mocker,
            fields=(None, "Failed to read item: [ERROR] you aren't currently signed in"),
        )
        result = CliRunner().invoke(cli, ["secrets", "get", "op://vault/item", "--fields", "username"])
        assert result.exit_code == 1
        assert "op signin" in result.output

    def test_normal_lookup_error_omits_setup_instructions(self, mocker):
        _patch_provider(mocker, fields=(None, "Failed to read item: item not found"))
        result = CliRunner().invoke(cli, ["secrets", "get", "op://vault/missing", "--fields", "username"])
        assert result.exit_code == 1
        assert "item not found" in result.output
        assert "Setup instructions" not in result.output

    def test_no_eager_is_available_call(self, mocker):
        provider = _patch_provider(mocker, fields=({"username": "admin"}, None))
        result = CliRunner().invoke(cli, ["secrets", "get", "op://vault/item", "--fields", "username"])
        assert result.exit_code == 0
        provider.is_available.assert_not_called()
