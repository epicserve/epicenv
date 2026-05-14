# epicenv

[![PyPI version](https://img.shields.io/pypi/v/epicenv)](https://pypi.org/project/epicenv/)
[![Python versions](https://img.shields.io/pypi/pyversions/epicenv)](https://pypi.org/project/epicenv/)
[![Tests](https://github.com/epicserve/epicenv/actions/workflows/test.yml/badge.svg)](https://github.com/epicserve/epicenv/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Schema-based environment variable management for Python projects. Define your environment variables in `pyproject.toml` (or a dedicated `.env.toml`) with types, defaults, and help text. Use epicenv to create, validate, and manage `.env` files.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Why epicenv?](#why-epicenv)
- [CLI Commands](#cli-commands)
- [Schema Basics](#schema-basics)
- [Built-in Initializers](#built-in-initializers)
- [Framework Examples](#framework-examples)
- [Validation](#validation)
- [Documentation](#documentation)

## Installation

```bash
# Run without installing
uvx epicenv create

# Or install as a dependency
uv add epicenv

# For Django projects (adds dj-database-url, dj-email-url support)
uv add epicenv[django]
```

## Quick Start

**1. Define your schema in `pyproject.toml`:**

```toml
[tool.epicenv.variables]
SECRET_KEY = {
    type = "str",
    required = true,
    help_text = "Secret key for cryptographic signing",
    initial_func = "epicenv.initializers.url_safe_password"
}

DEBUG = { type = "bool", default = false, initial = "on" }
DATABASE_URL = { type = "str", default = "sqlite:///db.sqlite3" }
```

**2. Generate your `.env` file:**

```bash
uvx epicenv create
```

**3. Use in your code:**

```python
from epicenv import Env

env = Env()
env.read_env()

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
```

## Why epicenv?

| Traditional `.env.example` workflow | With epicenv |
|-------------------------------------|--------------|
| Copy `.env.example` to `.env` | Run `epicenv create` |
| Manually generate secrets | Auto-generated via initializers |
| Templates get out of date | Schema is the single source of truth |
| Runtime errors from missing vars | `epicenv validate` catches mistakes early |
| No documentation for variables | Help text in schema, shown in `.env` |

## CLI Commands

```bash
epicenv create                    # Create .env from schema
epicenv create --path config/.env # Create at specific path
epicenv create --no-backup        # Don't backup existing file

epicenv diff                      # Compare .env with schema
epicenv validate                  # Validate environment against schema
epicenv validate --strict         # Exit with error if validation fails
```

## Schema Basics

Define variables in `[tool.epicenv.variables]`:

```toml
[tool.epicenv.variables]
MY_VAR = {
    type = "str",              # Required: str, bool, int, list, url, json, etc.
    required = true,           # Is this required? (default: true if no default)
    default = "value",         # Default for .env generation
    help_text = "Description", # Shown in generated .env
    initial = "value",         # Static initial value
    initial_func = "module.fn" # Dynamic initial value generator
}
```

**Supported types:** `str`, `bool`, `int`, `float`, `list`, `dict`, `json`, `url`, `uuid`, `path`, `date`, `datetime`, `log_level`, and Django types (`dj_db_url`, `dj_email_url`, `dj_cache_url`).

### Schema location

For projects with many variables, keep `pyproject.toml` tidy by moving the schema into a dedicated `.env.toml` file next to `pyproject.toml`. It's auto-discovered — no `pyproject.toml` change needed:

```toml
# .env.toml
[variables]
DEBUG = { type = "bool", default = false, initial = "on" }

# Table form is nice for variables with several fields:
[variables.SECRET_KEY]
type = "str"
required = true
help_text = "Secret key for cryptographic signing"
initial_func = "epicenv.initializers.url_safe_password"
```

Or point at a custom path:

```toml
# pyproject.toml
[tool.epicenv]
config_file = "config/env-schema.toml"
```

See [Schema Reference](docs/schema-reference.md) for complete field documentation and discovery rules.

## Built-in Initializers

### url_safe_password

Generate URL-safe random passwords:

```toml
SECRET_KEY = {
    type = "str",
    initial_func = "epicenv.initializers.url_safe_password"
}

# Custom length (default: 50)
API_TOKEN = {
    type = "str",
    initial_func = "epicenv.initializers.url_safe_password",
    kwargs = { length = 32 }
}
```

### 1Password

Fetch secrets from 1Password CLI during `.env` generation:

```toml
STRIPE_API_KEY = {
    type = "str",
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Production/Stripe/api_key"]
}
```

Requires [1Password CLI](https://developer.1password.com/docs/cli/get-started/) installed and signed in. Falls back to placeholder if unavailable.

See [1Password Integration](docs/1password.md) for setup and troubleshooting.

### Custom Initializers

Use any Python callable:

```toml
SECRET_KEY = { type = "str", initial_func = "secrets.token_urlsafe" }
DJANGO_KEY = { type = "str", initial_func = "django.core.management.utils.get_random_secret_key" }
CUSTOM = { type = "str", initial_func = "myapp.utils.generate_key" }
```

## Framework Examples

### Django

```toml
# pyproject.toml
[tool.epicenv.variables]
SECRET_KEY = { type = "str", required = true, initial_func = "django.core.management.utils.get_random_secret_key" }
DEBUG = { type = "bool", default = false, initial = "on" }
DATABASE_URL = { type = "dj_db_url", default = "sqlite:///db.sqlite3" }
```

```python
# settings.py
from epicenv import Env

env = Env()
env.read_env()

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
DATABASES = {"default": env.dj_db_url("DATABASE_URL", default="sqlite:///db.sqlite3")}
```

See [Django Integration](docs/django.md) for complete setup including email and cache URLs.

### FastAPI / Flask

```toml
# pyproject.toml
[tool.epicenv.variables]
APP_NAME = { type = "str", default = "My API" }
API_HOST = { type = "str", default = "0.0.0.0" }
API_PORT = { type = "int", default = 8000 }
DATABASE_URL = { type = "url", required = true }
LOG_LEVEL = { type = "log_level", default = "INFO" }
```

```python
# config.py
from epicenv import Env

env = Env()
env.read_env()

APP_NAME = env.str("APP_NAME", default="My API")
DATABASE_URL = env.url("DATABASE_URL")
LOG_LEVEL = env.log_level("LOG_LEVEL", default="INFO")
```

## Validation

epicenv validates that variables used in code are defined in your schema. Control with `EPICENV_VALIDATE`:

| Mode | Behavior |
|------|----------|
| `auto` (default) | Validate when `DEBUG=true` |
| `strict` | Always validate, raise errors |
| `warn` | Always validate, warn only |
| `off` | Disable validation |

```bash
EPICENV_VALIDATE=strict python app.py  # Always validate
```

## Documentation

- [Schema Reference](docs/schema-reference.md) - Complete field types and options
- [1Password Integration](docs/1password.md) - Setup and troubleshooting
- [Django Integration](docs/django.md) - Django-specific features and legacy commands

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgments

epicenv is built on top of [environs](https://github.com/sloria/environs), which provides the core environment variable parsing functionality.

## License

MIT License
