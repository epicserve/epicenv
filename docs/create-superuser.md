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

# Optional: Docker Compose service name
# If set, Django runs in container via 'docker compose exec'
# Can be overridden with --compose-service flag
compose_service = "web"

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
  --reference TEXT         Override 1Password reference
  --settings TEXT          Django settings module (e.g., 'myproject.settings')
  --compose-service TEXT   Docker Compose service name (e.g., 'web')
  --help                   Show this message and exit
```

The `--compose-service` option runs Django code inside a Docker container while keeping 1Password CLI on the host.

### Configuration Priority

When `compose_service` is configured in both places:

1. **CLI flag** takes precedence (overrides config)
2. **Config file** provides default
3. **Neither** = runs locally

Examples:
```bash
# Config: compose_service = "web"

epicenv create-superuser              # Uses "web" from config
epicenv create-superuser --compose-service api  # Uses "api" (overrides)
epicenv create-superuser              # If no config: runs locally
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

## How It Works

The `epicenv create-superuser` command uses a subprocess approach:

1. **Fetch credentials** from 1Password using the 1Password CLI
2. **Load environment** variables from your epicenv configuration
3. **Execute Django** code in a subprocess to create/update the superuser
4. **Idempotent** operation - safely creates or updates as needed

This means:
- 1Password CLI must be available where the command runs
- Django must be installed in the Python environment
- Works identically in local and containerized environments

## Docker and Docker Compose

For containerized Django applications, use the `--compose-service` flag to run Django code in your container while keeping 1Password CLI on your host machine.

### Quick Example

```bash
# Run from host - 1Password stays on host, Django runs in container
epicenv create-superuser --compose-service web
```

**No 1Password CLI installation in containers needed!** ✨

### How It Works

```bash
epicenv create-superuser --compose-service web
```

1. **Fetches credentials** from 1Password on your **host** (where CLI is installed)
2. **Passes credentials** to your Docker container
3. **Executes Django** code inside the container via `docker compose exec -T`
4. **Uses container's environment** - `DJANGO_SETTINGS_MODULE` from docker-compose.yml

**Note**: The `--settings` flag is optional when using `--compose-service`. The container's `DJANGO_SETTINGS_MODULE` will be used unless you override it.

### Setup Requirements

- 1Password CLI installed **on host only** (not in containers)
- Docker Compose running
- `DJANGO_SETTINGS_MODULE` set in docker-compose.yml **(not required on host)**

**docker-compose.yml example:**
```yaml
services:
  web:
    environment:
      DJANGO_SETTINGS_MODULE: myproject.settings
```

### Usage Examples

```bash
# Basic usage
epicenv create-superuser --compose-service web

# With specific settings
epicenv create-superuser --compose-service web --settings myproject.prod_settings

# With custom reference
epicenv create-superuser --compose-service web --reference "op://Production/Admin"
```

### Complete Guide

For comprehensive Docker Compose setup including:
- Complete docker-compose.yml and Dockerfile examples
- Development and production deployment patterns
- CI/CD integration with GitHub Actions
- Troubleshooting Docker-specific issues
- Helper scripts for development setup

See the **[Docker Compose Guide](docker-compose.md)**.
