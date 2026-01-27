# Create Superuser Command

The `epicenv create-superuser` command creates or updates a Django superuser using credentials stored in 1Password.

## Quick Start

1. Store your superuser credentials in 1Password with fields:
   - `username`
   - `email`
   - `password`

2. Configure in `pyproject.toml`:
   ```toml
   [tool.epicenv.django]
   superuser_reference = "op://Development/Django Admin"
   ```

3. Run the command:
   ```bash
   epicenv create-superuser
   ```

## Configuration

### pyproject.toml

```toml
[tool.epicenv.django]
# Required: 1Password reference to the item containing credentials
superuser_reference = "op://vault/item"

# Optional: Fields to check for existing users (default: ["username"])
superuser_lookup_fields = ["username", "email"]

# Optional: Custom field names in 1Password
[tool.epicenv.django.superuser_fields]
username = "username"
email = "email"
password = "password"
```

### CLI Options

```bash
epicenv create-superuser [OPTIONS]

Options:
  --reference TEXT   Override 1Password reference
  --settings TEXT    Django settings module (e.g., 'myproject.settings')
  --help             Show this message and exit
```

## Idempotent Behavior

The command is designed to be safely run multiple times:

- **If no user exists**: Creates a new superuser
- **If user exists** (by username or email): Updates their password

This makes it safe to use in deployment scripts or development setup.

## Custom User Models

The command automatically uses Django's `get_user_model()` function, so it works with custom user models that follow Django's conventions.

## 1Password Item Structure

Your 1Password item should have three fields:

| Field | Description |
|-------|-------------|
| `username` | The superuser's username |
| `email` | The superuser's email address |
| `password` | The superuser's password |

If your 1Password item uses different field names, configure them in `pyproject.toml`:

```toml
[tool.epicenv.django.superuser_fields]
username = "user"      # Field name for username
email = "mail"         # Field name for email
password = "pass"      # Field name for password
```

## Troubleshooting

### "Django is not installed"

Install Django:
```bash
pip install django
```

### "DJANGO_SETTINGS_MODULE not set"

Either set the environment variable:
```bash
export DJANGO_SETTINGS_MODULE=myproject.settings
epicenv create-superuser
```

Or use the `--settings` flag:
```bash
epicenv create-superuser --settings myproject.settings
```

### "Database connection failed"

Ensure your database is running and `DATABASE_URL` (or Django's `DATABASES` setting) is configured correctly.

### "User table does not exist"

Run Django migrations first:
```bash
python manage.py migrate
```

### "1Password CLI not available"

1. Install the 1Password CLI: https://developer.1password.com/docs/cli/get-started/
2. Sign in: `op signin`

### "Field not found in 1Password"

Verify that your 1Password item has the required fields (username, email, password) or configure custom field names in `pyproject.toml`.
