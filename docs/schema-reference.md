# Schema Reference

This document provides a complete reference for defining environment variable schemas in `pyproject.toml`.

## Field Types

All [environs](https://github.com/sloria/environs) types are supported:

| Category | Types |
|----------|-------|
| **Basic** | `str`, `bool`, `int`, `float`, `decimal` |
| **Collections** | `list`, `dict`, `json` |
| **Date/Time** | `date`, `datetime`, `time`, `timedelta` |
| **Specialized** | `url`, `uuid`, `path`, `enum`, `log_level` |
| **Django** | `dj_db_url`, `dj_email_url`, `dj_cache_url` (requires `[django]` extra) |

## Schema Fields

Each variable in your schema can have these fields:

```toml
[tool.epicenv.variables]
MY_VARIABLE = {
    type = "str",              # Variable type (required)
    required = true,           # Is this variable required? (default: true if no default)
    default = "value",         # Default value for .env generation and diff
    help_text = "Description", # Documentation for this variable
    initial = "initial_value", # Static initial value for .env generation
    initial_func = "module.function",  # Callable for dynamic initial values
    args = ["arg1", "arg2"],   # Positional arguments for initial_func
    kwargs = { key = "value" } # Keyword arguments for initial_func
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | **Required.** The variable type (see Field Types above) |
| `required` | boolean | Whether the variable must have a value. Defaults to `true` if no default is provided |
| `default` | any | Default value used for `.env` generation and `epicenv diff` |
| `help_text` | string | Documentation shown in generated `.env` files |
| `initial` | string | Static initial value written to `.env` during creation |
| `initial_func` | string | Python callable path for dynamic initial values |
| `args` | list | Positional arguments passed to `initial_func` |
| `kwargs` | object | Keyword arguments passed to `initial_func` |

## Understanding `default` vs Runtime Defaults

The `default` field in `pyproject.toml` is **only used for `.env` file generation and diff commands**. It is NOT used at runtime.

Runtime defaults must always be specified in your Python code:

```python
# Runtime default is specified here, not in pyproject.toml
DEBUG = env.bool("DEBUG", default=False)

# This allows for dynamic defaults based on other values
SECURE_COOKIES = env.bool("SECURE_COOKIES", default=not DEBUG)
```

**Why this design?**

1. **Single source of truth** - Your code is authoritative for runtime behavior
2. **Dynamic defaults** - Runtime defaults can depend on other values
3. **No confusion** - Clear separation between "what goes in .env" vs "what happens at runtime"

## Initial Values

### Static Initial Values

Use `initial` for simple static values:

```toml
[tool.epicenv.variables]
DEBUG = {
    type = "bool",
    default = false,
    initial = "on",  # Written to .env during creation
    help_text = "Enable debug mode"
}
```

### Dynamic Initial Values with `initial_func`

Use `initial_func` to generate values dynamically when running `epicenv create`:

```toml
[tool.epicenv.variables]
# Python stdlib
SECRET_KEY = {
    type = "str",
    initial_func = "secrets.token_urlsafe"
}

# Django's secret key generator
DJANGO_SECRET = {
    type = "str",
    initial_func = "django.core.management.utils.get_random_secret_key"
}

# Your own function
CUSTOM_VALUE = {
    type = "str",
    initial_func = "myapp.utils.generate_api_key"
}
```

### Passing Arguments to `initial_func`

Use `args` and `kwargs` to pass arguments:

```toml
[tool.epicenv.variables]
# With positional argument
API_TOKEN = {
    type = "str",
    initial_func = "epicenv.initializers.url_safe_password",
    kwargs = { length = 32 }
}

# With keyword arguments
OP_SECRET = {
    type = "str",
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Vault/Item/field"],
    kwargs = { fallback = "local_dev_value" }
}
```

## Complete Example

```toml
[tool.epicenv.variables]
# Required with auto-generated initial value
SECRET_KEY = {
    type = "str",
    required = true,
    help_text = "Secret key for cryptographic signing",
    initial_func = "epicenv.initializers.url_safe_password"
}

# Optional with default (commented out in .env)
DEBUG = {
    type = "bool",
    default = false,
    initial = "on",
    help_text = "Enable debug mode (never enable in production)"
}

# Required with no initial (user must fill in)
API_KEY = {
    type = "str",
    required = true,
    help_text = "API key for external service"
}

# Database URL with default
DATABASE_URL = {
    type = "dj_db_url",
    default = "sqlite:///db.sqlite3",
    help_text = "Database connection URL"
}

# List type
ALLOWED_HOSTS = {
    type = "list",
    default = ["localhost", "127.0.0.1"],
    help_text = "Comma-separated list of allowed hosts"
}

# Log level with default
LOG_LEVEL = {
    type = "log_level",
    default = "INFO",
    help_text = "Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
}
```
