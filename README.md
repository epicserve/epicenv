# epicenv

Schema-based environment variable management for Python projects.

Define your environment variables in `pyproject.toml` with types, defaults, and help text. Use epicenv to create, validate, and manage `.env` files. Works with any Python project - Django, FastAPI, Flask, or plain Python.

## Features

- 📋 **Schema-based**: Define variables in `pyproject.toml` with types, defaults, and documentation
- ✅ **Validation**: Catch undefined variables in debug mode before they cause runtime errors
- 🛠️ **CLI Tools**: Create and compare `.env` files with `uvx epicenv create` and `uvx epicenv diff`
- 🎯 **Framework Agnostic**: Works with Django, FastAPI, Flask, or any Python project
- 🔧 **Flexible**: Use schema-only, code-only, or hybrid approaches
- 🐍 **Type Safe**: Full type support (str, bool, int, list, url, json, etc.)

## Quick Start

### 1. Define your schema in `pyproject.toml`

```toml
[tool.epicenv.variables]
SECRET_KEY = {
    type = "str",
    required = true,
    help_text = "Secret key for cryptographic signing",
    initial_func = "secrets.token_urlsafe"
}

DEBUG = {
    type = "bool",
    default = false,
    initial = "on",
    help_text = "Enable debug mode (never enable in production)"
}

DATABASE_URL = {
    type = "dj_db_url",
    default = "sqlite:///db.sqlite3",
    help_text = "Database connection URL"
}

API_KEY = {
    type = "str",
    required = true,
    help_text = "API key for external service"
}
```

### 2. Create a `.env` file

Use `uvx` to run without installing:

```bash
uvx epicenv create
```

Or install and use directly:

```bash
uv add epicenv
epicenv create
```

This generates a `.env` file with help text, types, and initial values:

```bash
# This is an initial .env file generated on 2026-01-24...
# Any environment variable with a default can be safely removed or commented out.

# Secret key for cryptographic signing
# type: str
SECRET_KEY=hkXzH0ZFG1YOtKhDsXAqS7rkt50_fZu_bV8YzPXr7VA

# Enable debug mode (never enable in production)
# type: bool
# default: False
DEBUG=on

# Database connection URL
# type: dj_db_url
# default: sqlite:///db.sqlite3
# DATABASE_URL=

# API key for external service
# type: str
API_KEY=
```

### 3. Use in your code

```python
from epicenv import Env

env = Env()
env.read_env()  # Load from .env file

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
DATABASE_URL = env.str("DATABASE_URL", default="sqlite:///db.sqlite3")
API_KEY = env.str("API_KEY")
```

### 4. Validate your environment

Check for missing required variables:

```bash
epicenv validate
```

Compare your `.env` file with the schema:

```bash
epicenv diff
```

## Installation

### For any Python project

```bash
uv add epicenv
```

### For Django projects (with dj-database-url, dj-email-url support)

```bash
uv add epicenv[django]
```

### Without installation (using uvx)

```bash
uvx epicenv create
uvx epicenv diff
uvx epicenv validate
```

## CLI Commands

### `epicenv create`

Create a `.env` file from your `pyproject.toml` schema.

```bash
epicenv create                    # Create .env in current directory
epicenv create --path config/.env # Create at specific path
epicenv create --no-backup        # Don't backup existing file
```

### `epicenv diff`

Compare your `.env` file with the schema and show differences.

```bash
epicenv diff                    # Compare .env with schema
epicenv diff --path config/.env # Compare specific file
```

Output:

```
✓ All variables are in sync!
```

or

```
Missing required variables:
  • API_KEY - API key for external service

Missing optional variables (have defaults):
  • DATABASE_URL (default: sqlite:///db.sqlite3) - Database connection URL

Variables in .env file not defined in schema:
  • OLD_VARIABLE
```

### `epicenv validate`

Validate current environment against schema.

```bash
epicenv validate          # Validate environment
epicenv validate --strict # Exit with error code if validation fails
```

## Validation Mode

Validation is automatically enabled when `DEBUG=true`. Control validation behavior with the `EPICENV_VALIDATE` environment variable:

- `auto` (default): Validate when `DEBUG=true`, otherwise no validation
- `strict`: Always validate and raise errors for undefined variables
- `warn`: Always validate but only warn (don't raise errors)
- `off`: Disable validation completely

```bash
# Auto mode (default) - validates only when DEBUG=true
DEBUG=true python manage.py runserver  # Validates!
DEBUG=false python manage.py runserver # No validation

# Force strict validation regardless of DEBUG
EPICENV_VALIDATE=strict python manage.py runserver

# Warn about undefined variables but don't fail
EPICENV_VALIDATE=warn python manage.py runserver

# Disable validation completely
EPICENV_VALIDATE=off python manage.py runserver
```

In your code:

```python
from epicenv import Env

env = Env()  # Validation mode controlled by EPICENV_VALIDATE env var
env.read_env()

# If MY_VAR is not in pyproject.toml schema and validation is enabled:
value = env.str("MY_VAR")  # UndefinedVariableError!
```

Error message:

```
UndefinedVariableError: Environment variable 'MY_VAR' is not defined in pyproject.toml schema.

Add it to [tool.epicenv.variables] in your pyproject.toml:

[tool.epicenv.variables]
MY_VAR = { type = "str", help_text = "Description here" }

Or disable validation by setting EPICENV_VALIDATE=off
```

## Schema Reference

### Field Types

All [environs](https://github.com/sloria/environs) types are supported:

- Basic: `str`, `bool`, `int`, `float`, `decimal`
- Collections: `list`, `dict`, `json`
- Date/Time: `date`, `datetime`, `time`, `timedelta`
- Specialized: `url`, `uuid`, `path`, `enum`, `log_level`
- Django (with `[django]` extra): `dj_db_url`, `dj_email_url`, `dj_cache_url`

### Schema Fields

```toml
[tool.epicenv.variables]
MY_VARIABLE = {
    type = "str",              # Variable type (required)
    required = true,           # Is this variable required? (default: true if no default)
    default = "value",         # Default value if not set
    help_text = "Description", # Documentation for this variable
    initial = "initial_value", # Static initial value for .env generation
    initial_func = "module.function"  # Callable for dynamic initial values
}
```

### Initial Value Functions

Use `initial_func` to generate dynamic values:

```toml
[tool.epicenv.variables]
SECRET_KEY = {
    type = "str",
    initial_func = "secrets.token_urlsafe"  # Python stdlib
}

DJANGO_SECRET = {
    type = "str",
    initial_func = "django.core.management.utils.get_random_secret_key"
}

CUSTOM_VALUE = {
    type = "str",
    initial_func = "myapp.utils.generate_api_key"  # Your own function
}
```

## Django Integration

### Option 1: Schema-based (Recommended)

Define variables in `pyproject.toml` and use the Env class:

```python
# settings.py
from pathlib import Path
from epicenv import Env

BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()  # Validation automatically enabled when DEBUG=true
env.read_env(BASE_DIR / ".env")

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
DATABASES = {"default": env.dj_db_url("DATABASE_URL", default="sqlite:///db.sqlite3")}
```

Then use CLI commands:

```bash
epicenv create  # Instead of ./manage.py create_env_file
epicenv diff    # Instead of ./manage.py diff_env_file
```

### Option 2: Django Management Commands (Legacy)

For backward compatibility, Django management commands still work:

```python
# settings.py
INSTALLED_APPS = [
    ...
    "epicenv",  # Add to INSTALLED_APPS
]

from epicenv import Env

env = Env()
env.read_env(BASE_DIR / ".env")

# Use help_text, initial, initial_func as before
SECRET_KEY = env.str(
    "SECRET_KEY",
    initial_func="django.core.management.utils.get_random_secret_key",
    help_text="Django's secret key",
)
```

Then use Django commands:

```bash
./manage.py create_env_file
./manage.py diff_env_file
```

## Examples

### FastAPI Project

```toml
# pyproject.toml
[tool.epicenv.variables]
APP_NAME = { type = "str", default = "My API", help_text = "Application name" }
API_HOST = { type = "str", default = "0.0.0.0", help_text = "API host" }
API_PORT = { type = "int", default = 8000, help_text = "API port" }
DATABASE_URL = { type = "url", required = true, help_text = "Database URL" }
REDIS_URL = { type = "url", default = "redis://localhost:6379", help_text = "Redis URL" }
LOG_LEVEL = { type = "log_level", default = "INFO", help_text = "Logging level" }
```

```python
# config.py
from epicenv import Env

env = Env()
env.read_env()

APP_NAME = env.str("APP_NAME", default="My API")
API_HOST = env.str("API_HOST", default="0.0.0.0")
API_PORT = env.int("API_PORT", default=8000)
DATABASE_URL = env.url("DATABASE_URL")
REDIS_URL = env.url("REDIS_URL", default="redis://localhost:6379")
LOG_LEVEL = env.log_level("LOG_LEVEL", default="INFO")
```

### Flask Project

```toml
# pyproject.toml
[tool.epicenv.variables]
FLASK_APP = { type = "str", default = "app.py", help_text = "Flask app entry point" }
FLASK_ENV = { type = "str", default = "production", help_text = "Flask environment" }
SECRET_KEY = { type = "str", required = true, help_text = "Flask secret key", initial_func = "secrets.token_hex" }
DATABASE_URL = { type = "url", required = true, help_text = "Database URL" }
```

```python
# config.py
from epicenv import Env

env = Env()
env.read_env()

class Config:
    FLASK_APP = env.str("FLASK_APP", default="app.py")
    FLASK_ENV = env.str("FLASK_ENV", default="production")
    SECRET_KEY = env.str("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = env.url("DATABASE_URL")
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
