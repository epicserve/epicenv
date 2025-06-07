set dotenv-load := true

@_default:
    just --list

@_success message:
    echo "\033[0;32m{{ message }}\033[0m"

@_start_command message:
    just _success "\n{{ message }} ..."

format: format_just format_python

@format_just:
    just _start_command "Formatting Justfile"
    just --fmt --unstable

@format_python:
    just _start_command "Formatting Python"
    uv run ruff format

@lint: lint_python

@lint_python:
    just _start_command "Linting Python"
    uv run ruff check

@pre_commit: format lint test

publish:
    #!/usr/bin/env bash
    echo -e '\nTo publish to PyPI, first run `just version_bump <major|minor|patch>` and push up the '\
    "changes, then create a release in GitHub (https://github.com/epicserve/django-envtools/releases).\n"

@test *FLAGS:
    uv run pytest {{ FLAGS }}

@test_with_coverage:
    uv run pytest --cov --cov-config=pyproject.toml --cov-report=html
    open htmlcov/index.html

# Update the version of the project (bump can be 'major', 'minor', or 'patch')
version_bump bump:
    #!/usr/bin/env bash
    just _start_command "Bumping version"
    OLD_VERSION=$(uv version | awk '{print $2}')
    echo "Current version: v${OLD_VERSION}"
    uv version --bump {{ bump }}
    git add pyproject.toml uv.lock
    NEW_VERSION=$(uv version | awk '{print $2}')
    COMMIT_MESSAGE="Bumped version: v${OLD_VERSION} → v${NEW_VERSION}"
    git commit -m "${COMMIT_MESSAGE}"
    git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"
    just _start_command "${COMMIT_MESSAGE}"
