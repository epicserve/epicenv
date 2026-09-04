set dotenv-load

@_default:
    just --list

@_success message:
    printf "\033[0;32m%s\033[0m\n" "{{ message }}"

@_start_command message:
    printf "\n\033[0;32m%s ...\033[0m\n" "{{ message }}"

format: format_just format_python

@format_just:
    just _start_command "Formatting Justfile"
    just --fmt --unstable

@format_python:
    just _start_command "Formatting Python"
    uv run ruff check --select I --fix
    uv run ruff format

@lint: lint_python

@lint_python:
    just _start_command "Linting Python"
    uv run ruff check
    uv run ruff format --check

@pre_commit: format lint test

# Releases are automated: bump, push the tag, GitHub Actions publishes to PyPI
publish:
    #!/usr/bin/env bash
    echo -e '\nReleases are automated. Run `just version_bump <major|minor|patch>`,'\
    'then `git push origin main vX.Y.Z`. The tag push publishes to PyPI and creates'\
    'the GitHub Release. See CLAUDE.md for the full process.\n'

@test *FLAGS:
    uv run pytest {{ FLAGS }}

@test_with_coverage:
    uv run pytest --cov --cov-config=pyproject.toml --cov-report=html
    open htmlcov/index.html

# Bump the version (bump can be 'major', 'minor', or 'patch'), commit, and tag
version_bump bump:
    #!/usr/bin/env bash
    set -euo pipefail
    just _start_command "Bumping version"
    if [ -n "$(git status --porcelain -- ':!CHANGELOG.md')" ]; then
        echo "Error: working tree has changes beyond CHANGELOG.md. Commit or stash them first." >&2
        exit 1
    fi
    OLD_VERSION=$(uv version --short)
    uv version --bump {{ bump }}
    NEW_VERSION=$(uv version --short)
    git add pyproject.toml uv.lock CHANGELOG.md
    git commit -m "Bump version to v${NEW_VERSION}"
    git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"
    echo "Bumped v${OLD_VERSION} → v${NEW_VERSION}."
    echo "Now run: git push origin main v${NEW_VERSION}"
