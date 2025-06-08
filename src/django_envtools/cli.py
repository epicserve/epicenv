import re
from datetime import datetime
from pathlib import Path

import typer

from django_envtools import get_dot_env_file_str
from django_envtools.env_parse import get_env_calls

app = typer.Typer(help="Django-envtools CLI for managing environment variables")


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Django-envtools CLI for managing environment variables."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def _get_settings_content(settings_path: str) -> str:
    """Read the content of the settings file."""
    try:
        with open(settings_path) as f:
            return f.read()
    except FileNotFoundError:
        typer.secho(f"Settings file not found: {settings_path}", fg=typer.colors.RED)
        raise
    except Exception as e:
        typer.secho(f"Error reading settings file: {e}", fg=typer.colors.RED)
        raise


@app.command()
def create_env_file(settings_path: str = typer.Argument(help="The path to your python settings file.")):
    """Either print or write to a file the initial .env file."""
    cwd = Path.cwd()

    settings_content = _get_settings_content(settings_path)

    # Convert settings_content to an AST to extract all code where the Env class is used.
    try:
        env_calls = get_env_calls(settings_content)
    except SyntaxError as e:
        typer.secho(f"Error parsing settings file: {e}", fg=typer.colors.RED)
        return

    dot_env_file_str = get_dot_env_file_str(env_calls)
    env_path = cwd / ".env"
    env_path_rel_str = str(env_path.relative_to(cwd))

    if env_path.exists() is True:
        # move file to a backup file
        now = datetime.now()
        new_file_path = env_path.with_name(f".env.{now.strftime('%Y%m%d%H%M%S')}")
        env_path.rename(new_file_path)

        new_file_path_rel_str = str(new_file_path.relative_to(cwd))
        typer.secho(
            f"File {env_path_rel_str} already exists and was backed up to {new_file_path_rel_str}.\n",
            fg=typer.colors.YELLOW,
            err=True,
        )

    env_path.write_text(dot_env_file_str)
    typer.secho(f"{env_path_rel_str} file created.", fg=typer.colors.GREEN)


@app.command()
def diff_env_file(settings_path: str = typer.Argument(help="The path to your python settings file.")):
    """Show differences between your .env file and env variables in your Django settings."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        typer.secho(f"{env_path} does not exist.", fg=typer.colors.RED)
        return

    env_content = env_path.read_text()
    env_lines = env_content.splitlines()
    settings_content = _get_settings_content(settings_path)
    env_variables = get_env_calls(settings_content)

    existing_vars = []
    for line in env_lines:
        if re.match(r"^(#\s)?[_A-Z]+=.*", line) is not None:
            key, value = line.split("=", 1)
            existing_vars.append(key)

    missing_vars = []
    missing_default_vars = []
    for key, value in env_variables.items():
        has_default = value.get("default") is not None
        if has_default is True and (f"# {key}" not in existing_vars and key not in existing_vars):
            missing_default_vars.append(key)
        elif has_default is False and key not in existing_vars:
            missing_vars.append(key)

    if missing_vars:
        typer.secho("Environment variables Missing in .env file:", fg=typer.colors.YELLOW)
        for var in missing_vars:
            typer.echo(f"- {var}")

    if missing_default_vars:
        typer.secho("Environment variables Missing in .env file with default values:", fg=typer.colors.YELLOW)
        for var in missing_default_vars:
            typer.echo(f"- {var}")

    if not missing_vars and not missing_default_vars:
        typer.secho("All environment variables are set.", fg=typer.colors.GREEN)

    orphaned_vars = [key for key in existing_vars if key.replace("# ", "") not in env_variables]
    if orphaned_vars:
        typer.secho(
            "\nEnvironment variables in .env file that are not defined in your Django settings:",
            fg=typer.colors.YELLOW,
        )
        for var in orphaned_vars:
            typer.echo(f"- {var.replace('# ', '')}")


def main():
    app()


if __name__ == "__main__":
    main()
