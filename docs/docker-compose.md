# Using epicenv with Docker Compose

This guide shows how to use epicenv's `create-superuser` command with Docker Compose, keeping 1Password CLI on your host machine.

## Overview

The `epicenv create-superuser --compose-service <service>` command:

1. **Runs on your host** where 1Password CLI is installed
2. **Fetches credentials** from 1Password on the host
3. **Executes Django code** inside your Docker container via `docker compose exec`

**No 1Password CLI installation in containers required!** ✨

## Quick Start

```bash
# On your host machine (where 1Password CLI is installed)
epicenv create-superuser --compose-service web

# That's it! No 1Password in containers needed.
```

## Prerequisites

- Docker and Docker Compose installed
- 1Password CLI installed **on host only** (not in containers)
- Django project with epicenv configured in [pyproject.toml](../README.md#quick-start)
- epicenv installed **on host** (you can optionally install it in containers too)
- `DJANGO_SETTINGS_MODULE` set in docker-compose.yml **(not required on host)**

## Setup

### docker-compose.yml

Simple configuration - no 1Password mounts needed:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myapp
      POSTGRES_PASSWORD: devpassword
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    environment:
      DATABASE_URL: postgres://myapp:devpassword@db:5432/myapp
      DJANGO_SETTINGS_MODULE: myproject.settings
    ports:
      - "8000:8000"
    depends_on:
      - db

volumes:
  postgres_data:
```

### Dockerfile

No special 1Password configuration needed:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN pip install uv && uv sync --frozen

COPY . /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## Configuration

### pyproject.toml

```toml
[tool.epicenv.django]
superuser_reference = "op://Development/Django Admin"
superuser_lookup_fields = ["username", "email"]

# NEW: Set default Docker Compose service
compose_service = "web"

[tool.epicenv.django.superuser_fields]
username = "username"
email = "email"
password = "password"
```

With `compose_service` configured, you don't need the flag:

```bash
# Before (flag required every time)
epicenv create-superuser --compose-service web

# After (uses config default)
epicenv create-superuser

# Can still override
epicenv create-superuser --compose-service api
```

**Note**: The `--settings` flag is optional when using `--compose-service`. The command uses the container's `DJANGO_SETTINGS_MODULE` from docker-compose.yml unless you override it with `--settings`.

See [create-superuser documentation](create-superuser.md) for more configuration options.

## Usage

### Basic Workflow

**Step 1: Sign in to 1Password (on host machine)**
```bash
op signin
```

**Step 2: Build and start services**
```bash
docker compose build
docker compose up -d
```

**Step 3: Run migrations**
```bash
docker compose exec web python manage.py migrate
```

**Step 4: Create superuser (from host)**
```bash
epicenv create-superuser --compose-service web
```

Expected output:
```
Fetching credentials from 1Password: op://Development/Django Admin
Success! Created superuser: admin
```

### Command Options

```bash
# Basic usage
epicenv create-superuser --compose-service web

# With explicit reference
epicenv create-superuser --compose-service web --reference "op://vault/item"

# With specific Django settings
epicenv create-superuser --compose-service web --settings myproject.prod_settings

# All together
epicenv create-superuser \
  --compose-service web \
  --reference "op://Production/Django Admin" \
  --settings myproject.prod_settings
```

## Development Helper Script

Create a convenience script for development setup:

**scripts/setup-dev.sh:**
```bash
#!/bin/bash
set -e

echo "🔐 Checking 1Password CLI..."
if ! command -v op &> /dev/null; then
    echo "❌ 1Password CLI not found. Install: https://developer.1password.com/docs/cli/get-started/"
    exit 1
fi

echo "✅ 1Password CLI found"

echo "🔑 Ensuring signed in to 1Password..."
if ! op vault list &> /dev/null; then
    echo "Please sign in to 1Password:"
    op signin
fi

echo "🐳 Building containers..."
docker compose build

echo "⏳ Starting services..."
docker compose up -d

echo "⏳ Waiting for database to be ready..."
sleep 5  # Give database time to initialize

echo "🔄 Running migrations..."
docker compose exec -T web python manage.py migrate

echo "👤 Creating superuser..."
epicenv create-superuser --compose-service web

echo "✅ Development environment ready!"
echo "   Access admin: http://localhost:8000/admin"
```

Make it executable:
```bash
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh
```

## How It Works

The `--compose-service` flag changes the execution strategy:

### Without --compose-service (Local)
```bash
epicenv create-superuser
# → Runs: python -c "<django_script>" admin admin@example.com secret123
# → Django runs in your local Python environment
```

### With --compose-service (Docker)
```bash
epicenv create-superuser --compose-service web
# → Runs: docker compose exec -T web python -c "<django_script>" admin admin@example.com secret123
# → Django runs inside the 'web' container
# → 1Password CLI stays on host!
```

The command:
1. Fetches credentials from 1Password on **host** (where CLI is installed)
2. Passes credentials + environment to **container** via `docker compose exec`
3. Executes Django code **inside container** to create/update user

## Production Deployment

### Using 1Password Service Accounts

For production and CI/CD, use [1Password Service Accounts](https://developer.1password.com/docs/service-accounts/) on your deployment machine:

**1. Create a Service Account**

In 1Password, create a service account with read-only access to your secrets vault.

**2. Update deployment workflow**

```bash
# Set service account token on deployment machine
export OP_SERVICE_ACCOUNT_TOKEN="ops_..."

# Deploy containers
docker compose -f docker-compose.prod.yml up -d

# Run migrations and create superuser (from host)
docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate
epicenv create-superuser --compose-service web --settings myproject.prod_settings
```

### CI/CD Integration

**GitHub Actions example:**

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install 1Password CLI
        run: |
          curl -sSO https://downloads.1password.com/linux/debian/amd64/stable/1password-cli-amd64-latest.deb
          sudo dpkg -i 1password-cli-amd64-latest.deb

      - name: Install epicenv
        run: pip install epicenv

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Build and deploy
        env:
          OP_SERVICE_ACCOUNT_TOKEN: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
        run: |
          docker compose -f docker-compose.prod.yml build
          docker compose -f docker-compose.prod.yml up -d
          docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate

          # Create superuser from host using epicenv
          epicenv create-superuser --compose-service web
```

Store `OP_SERVICE_ACCOUNT_TOKEN` in GitHub Secrets.

## Comparison: Old vs New Approach

### ❌ Old Approach (Complicated)
```yaml
# docker-compose.yml - Had to mount 1Password session
services:
  web:
    volumes:
      - ~/.op:/root/.op:ro  # Mount 1Password session
```

```dockerfile
# Dockerfile - Had to install 1Password CLI
RUN curl -sSO https://downloads.1password.com/linux/debian/amd64/stable/1password-cli-amd64-latest.deb && \
    dpkg -i 1password-cli-amd64-latest.deb
```

```bash
# Had to run epicenv inside container
docker compose exec web epicenv create-superuser
```

### ✅ New Approach (Simple)
```yaml
# docker-compose.yml - No 1Password configuration needed!
services:
  web:
    # Just normal Django setup
```

```dockerfile
# Dockerfile - No 1Password installation needed!
# Just install your app dependencies
```

```bash
# Run from host - 1Password stays on host
epicenv create-superuser --compose-service web
```

**Benefits:**
- 🎯 Simpler Docker setup
- 🔒 1Password credentials never enter containers
- 📦 Smaller Docker images
- 🚀 Faster builds (no 1Password CLI installation)
- 🛡️ Better security posture

## Troubleshooting

### "1Password CLI is not available"

**Problem:** Command fails to fetch credentials from 1Password.

**Solution:** Ensure 1Password CLI is installed **on host** (not in container):
```bash
# On host
op --version

# Sign in if needed
op signin
```

### "docker: command not found"

**Problem:** Docker not available on host when using `--compose-service`.

**Solution:** Install Docker Desktop or Docker Engine on your host machine.

### "DJANGO_SETTINGS_MODULE not set"

**Problem:** Django can't find settings module in container.

**Solutions:**

1. **Set in docker-compose.yml**:
   ```yaml
   environment:
     DJANGO_SETTINGS_MODULE: myproject.settings
   ```

2. **Use --settings flag**:
   ```bash
   epicenv create-superuser --compose-service web --settings myproject.settings
   ```

### "Database connection failed"

**Problem:** Django can't connect to the database service.

**Solutions:**

1. **Check database is running:**
   ```bash
   docker compose ps
   docker compose logs db
   ```

2. **Verify DATABASE_URL:**
   ```bash
   docker compose exec web env | grep DATABASE_URL
   ```

3. **Ensure db service is ready:**
   ```bash
   # Wait for database to initialize
   docker compose up -d db
   sleep 10  # Give it time to start
   docker compose up -d web
   ```

### "User table does not exist"

**Problem:** Migrations haven't been run.

**Solution:**
```bash
docker compose exec web python manage.py migrate
```

### "service 'web' not found"

**Problem:** Service name doesn't match docker-compose.yml.

**Solution:** Use the exact service name from your docker-compose.yml:
```bash
# If your service is called 'django' instead of 'web'
epicenv create-superuser --compose-service django
```

## Best Practices

1. **Keep 1Password on host** - Never install 1Password CLI in containers
2. **Use service accounts in production** - Don't use personal 1Password sessions in CI/CD
3. **Run from host** - Always run `epicenv create-superuser --compose-service <name>` from host
4. **Run migrations first** - Ensure database tables exist before creating users
5. **Use environment variables** - Set `DJANGO_SETTINGS_MODULE` in docker-compose.yml
6. **Create setup scripts** - Automate the workflow for new developers

## Related Documentation

- [create-superuser Command](create-superuser.md)
- [1Password Integration](1password.md)
- [Django Integration](django.md)
- [1Password Service Accounts](https://developer.1password.com/docs/service-accounts/)
