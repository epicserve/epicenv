from pathlib import Path

from typer.testing import CliRunner

from django_envtools.cli import app

runner = CliRunner()


def test_diff_env_file(clean_env_files):
    project_root = Path.cwd()
    runner.invoke(app, ["create-env-file", "test_project/config/settings.py"])
    result = runner.invoke(app, ["diff-env-file", "test_project/config/settings.py"])
    assert "All environment variables are set." in result.output

    env_file = project_root / ".env"
    env_file_contents = env_file.read_text()

    env_file_contents = env_file_contents + "\n# NEW_VAR=NEW_VALUE\nFOO=BAR\n"
    env_file_contents = env_file_contents.replace("# DATABASE_URL=", "")
    env_file.write_text(env_file_contents)

    new_result = runner.invoke(app, ["diff-env-file", "test_project/config/settings.py"])
    assert ("Environment variables Missing in .env file with default values:\n- DATABASE_URL\n") in new_result.output

    assert (
        "Environment variables in .env file that are not defined in your Django settings:\n- NEW_VAR\n- FOO\n"
    ) in new_result.output

    for env_file in project_root.glob(".env*"):
        env_file.unlink()
