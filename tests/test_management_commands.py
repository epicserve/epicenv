import io
import re
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase


class TestCreateEnvFileCommand(TestCase):
    def tearDown(self):
        for path in Path.rglob(Path.cwd(), ".env*"):
            path.unlink()

    def test_create_env_file(self):
        call_command("create_env_file")
        env_file_content = (Path.cwd() / ".env").read_text()

        assert (
            re.search(
                r"# This is an initial \.env file generated on "
                r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}",
                env_file_content,
            )
            is not None
        )
        assert re.search(r"SECRET_KEY=.+\n", env_file_content) is not None

        assert ("# Set to `on` to enable debugging\n# type: bool\n# default: False\nDEBUG=on\n") in env_file_content

        assert (
            "# List of allowed hosts (e.g., `127.0.0.1,example.com`), see https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts for more information\n"  # noqa: E501
            "# type: list\n"
            "# default: []\n"
            "# ALLOWED_HOSTS=\n"
        ) in env_file_content

        assert (
            "# Database URL, see https://github.com/jazzband/dj-database-url for more information\n"
            "# type: dj_db_url\n"
            "# default: sqlite:///db.sqlite3\n"
            "# DATABASE_URL=\n"
        ) in env_file_content

        assert (
            "# See https://github.com/migonzalvar/dj-email-url for more examples on how to set the EMAIL_URL\n"
            "# type: dj_email_url\n"
            "# default: smtp://skroob@planetspaceball.com:12345@smtp.planetspaceball.com:587/?ssl=True&_default_from_email=President%20Skroob%20%3Cskroob@planetspaceball.com%3E\n"
            "# EMAIL_URL=\n"
        ) in env_file_content

    def test_diff_env_file(self):
        call_command("create_env_file")
        out = io.StringIO()
        call_command("diff_env_file", stdout=out)
        output = out.getvalue()
        assert "All environment variables are set." in output

        env_file = Path.cwd() / ".env"
        env_file_contents = env_file.read_text()

        env_file_contents = env_file_contents + "\n# NEW_VAR=NEW_VALUE\nFOO=BAR\n"
        env_file_contents = env_file_contents.replace("# DATABASE_URL=", "")
        env_file.write_text(env_file_contents)

        out = io.StringIO()
        call_command("diff_env_file", stdout=out)
        output = out.getvalue()

        assert ("Environment variables Missing in .env file with default values:\n- DATABASE_URL\n") in output

        assert (
            "Environment variables in .env file that are not defined in your Django settings:\n- NEW_VAR\n- FOO\n"
        ) in output
