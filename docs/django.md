# Django Integration

epicenv works with Django projects. Install with the Django extra to get `dj_db_url`, `dj_email_url`, and `dj_cache_url` type support.

## Installation

```bash
uv add epicenv[django]
```

## Recommended Setup (Schema-based)

Define your variables in `pyproject.toml` and use the CLI commands:

### 1. Define Schema

```toml
# pyproject.toml
[tool.epicenv.variables]
SECRET_KEY = {
    type = "str",
    required = true,
    help_text = "Django's secret key for cryptographic signing",
    initial_func = "django.core.management.utils.get_random_secret_key"
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

ALLOWED_HOSTS = {
    type = "list",
    default = ["localhost", "127.0.0.1"],
    help_text = "Comma-separated list of allowed hosts"
}

EMAIL_URL = {
    type = "dj_email_url",
    default = "consolemail://",
    help_text = "Email backend configuration URL"
}

CACHE_URL = {
    type = "dj_cache_url",
    default = "locmemcache://",
    help_text = "Cache backend configuration URL"
}
```

### 2. Use in settings.py

```python
# settings.py
from pathlib import Path
from epicenv import Env

BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()  # Validation enabled when DEBUG=true
env.read_env(BASE_DIR / ".env")

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

DATABASES = {
    "default": env.dj_db_url("DATABASE_URL", default="sqlite:///db.sqlite3")
}

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Email configuration
email_config = env.dj_email_url("EMAIL_URL", default="consolemail://")
EMAIL_BACKEND = email_config["EMAIL_BACKEND"]
EMAIL_HOST = email_config.get("EMAIL_HOST", "")
EMAIL_PORT = email_config.get("EMAIL_PORT", 25)
EMAIL_HOST_USER = email_config.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = email_config.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = email_config.get("EMAIL_USE_TLS", False)

# Cache configuration
CACHES = {
    "default": env.dj_cache_url("CACHE_URL", default="locmemcache://")
}
```

### 3. Create and Manage .env

```bash
# Create .env file from schema
epicenv create

# Compare .env with schema
epicenv diff

# Validate environment
epicenv validate
```

## Django URL Types

### dj_db_url

Database connection URLs parsed by [dj-database-url](https://github.com/jazzband/dj-database-url):

| Database | URL Format |
|----------|------------|
| PostgreSQL | `postgres://user:pass@host:5432/dbname` |
| MySQL | `mysql://user:pass@host:3306/dbname` |
| SQLite | `sqlite:///path/to/db.sqlite3` |

### dj_email_url

Email backend URLs parsed by [dj-email-url](https://github.com/migonzalvar/dj-email-url):

| Backend | URL Format |
|---------|------------|
| SMTP | `smtp://user:pass@host:587/?tls=True` |
| Console | `consolemail://` |
| File | `filemail:///path/to/emails` |
| In-memory | `memorymail://` |

### dj_cache_url

Cache backend URLs parsed by [django-cache-url](https://github.com/epicserve/django-cache-url):

| Backend | URL Format |
|---------|------------|
| Redis | `redis://host:6379/0` |
| Memcached | `memcached://host:11211` |
| Local memory | `locmemcache://` |
| File | `filecache:///path/to/cache` |

## Legacy Django Management Commands

For backward compatibility, epicenv provides Django management commands. This approach is **not recommended** for new projects - use the CLI commands instead.

### Setup

Add epicenv to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    ...
    "epicenv",
]
```

### Define Variables in Code

Instead of `pyproject.toml`, define variables with metadata directly in your settings:

```python
from epicenv import Env

env = Env()
env.read_env(BASE_DIR / ".env")

SECRET_KEY = env.str(
    "SECRET_KEY",
    initial_func="django.core.management.utils.get_random_secret_key",
    help_text="Django's secret key for cryptographic signing",
)

DEBUG = env.bool(
    "DEBUG",
    default=False,
    initial="on",
    help_text="Enable debug mode",
)

DATABASE_URL = env.dj_db_url(
    "DATABASE_URL",
    default="sqlite:///db.sqlite3",
    help_text="Database connection URL",
)
```

### Run Management Commands

```bash
# Create .env file
./manage.py create_env_file

# Compare .env with definitions
./manage.py diff_env_file
```

### Why This Is Legacy

The management command approach has limitations:

1. **Requires Django context** - Must import settings to run commands
2. **Circular dependencies** - Settings must be importable before `.env` exists
3. **Scattered definitions** - Variables defined in code, not centralized schema
4. **Less portable** - Can't use commands in non-Django contexts

The schema-based approach (`pyproject.toml` + CLI) solves all these issues.

## Validation

epicenv automatically validates environment variables when `DEBUG=true`. Control this with `EPICENV_VALIDATE`:

```bash
# Default: validate when DEBUG=true
DEBUG=true python manage.py runserver  # Validates

# Always validate
EPICENV_VALIDATE=strict python manage.py runserver

# Warn but don't fail
EPICENV_VALIDATE=warn python manage.py runserver

# Disable validation
EPICENV_VALIDATE=off python manage.py runserver
```

Validation catches variables used in code but not defined in your schema, helping prevent runtime errors from typos or missing configuration.
