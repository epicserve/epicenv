import re
from pathlib import Path

from typer.testing import CliRunner

from django_envtools.cli import app

runner = CliRunner()


def test_create_env_file(clean_env_files):
    project_root = Path.cwd()
    result = runner.invoke(app, ["create-env-file", "test_project/config/settings.py"])
    assert ".env file created." in result.output
    env_file_content = (project_root / ".env").read_text()

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
