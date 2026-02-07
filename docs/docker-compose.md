# Using epicenv with Docker Compose

This guide shows how to use epicenv's `create-superuser` command in containerized Django applications with Docker Compose.

## Overview

The `epicenv create-superuser` command fetches credentials from 1Password on your host machine, then uses subprocess to create the superuser in Django. This works seamlessly with Docker Compose by:

1. Running epicenv on your host machine (where 1Password CLI is available)
2. Loading environment variables from your epicenv configuration
3. Executing Django commands either locally or in containers

## Quick Start

```bash
# Run epicenv on host - it will create superuser in local Django environment
epicenv create-superuser

# For Docker Compose workflows, you'll need 1Password CLI accessible in the container
# Two approaches: mount ~/.op session OR install 1Password CLI in container
```

## Prerequisites

- Docker and Docker Compose installed
- 1Password CLI configured on host machine
- Django project with epicenv configured in [pyproject.toml](../README.md#quick-start)

## Setup Approaches

### Approach 1: Mount 1Password Session (Development - Recommended)

Best for local development. Your host machine's 1Password session is mounted into containers.

**docker-compose.yml:**
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
      # Mount 1Password session directory (read-only)
      - ~/.op:/root/.op:ro
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

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies including epicenv
RUN pip install uv && \
    uv sync --frozen

COPY . /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**Usage:**
```bash
# Sign in to 1Password on host
op signin

# Start services
docker compose up -d

# Run migrations
docker compose exec web python manage.py migrate

# Create superuser (epicenv inside container can access host's 1Password session)
docker compose exec web epicenv create-superuser
```

### Approach 2: Install 1Password CLI in Container

Best when you need 1Password CLI for other operations in the container.

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

# Install 1Password CLI
RUN apt-get update && \
    apt-get install -y curl && \
    curl -sSO https://downloads.1password.com/linux/debian/amd64/stable/1password-cli-amd64-latest.deb && \
    dpkg -i 1password-cli-amd64-latest.deb && \
    rm 1password-cli-amd64-latest.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY . /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**docker-compose.yml:**
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
      # Mount 1Password session
      - ~/.op:/root/.op:ro
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

## Configuration

### pyproject.toml

```toml
[tool.epicenv.django]
superuser_reference = "op://Development/Django Admin"
superuser_lookup_fields = ["username", "email"]

[tool.epicenv.django.superuser_fields]
username = "username"
email = "email"
password = "password"
```

See [create-superuser documentation](create-superuser.md) for more configuration options.

## Usage Workflow

### Initial Setup

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

**Step 4: Create superuser**
```bash
docker compose exec web epicenv create-superuser
```

Expected output:
```
Fetching credentials from 1Password: op://Development/Django Admin
Success! Created superuser: admin
```

### Development Helper Script

Create a convenience script for development setup:

**scripts/setup-dev.sh:**
```bash
#!/bin/bash
set -e

echo "🐳 Building containers..."
docker compose build

echo "⏳ Starting services..."
docker compose up -d

echo "⏳ Waiting for database to be ready..."
docker compose exec -T web python -c "
import time
from django.db import connection
for i in range(30):
    try:
        connection.ensure_connection()
        print('✅ Database ready!')
        break
    except Exception:
        if i == 29:
            raise
        time.sleep(1)
"

echo "🔄 Running migrations..."
docker compose exec -T web python manage.py migrate

echo "👤 Creating superuser..."
docker compose exec -T web epicenv create-superuser

echo "✅ Development environment ready!"
echo "   Access admin: http://localhost:8000/admin"
```

Make it executable:
```bash
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh
```

## Production Deployment

### Using 1Password Service Accounts

For production and CI/CD, use [1Password Service Accounts](https://developer.1password.com/docs/service-accounts/) instead of personal sessions:

**1. Create a Service Account**

In 1Password, create a service account with read-only access to your secrets vault.

**2. Update docker-compose.prod.yml**

```yaml
services:
  web:
    build: .
    environment:
      OP_SERVICE_ACCOUNT_TOKEN: ${OP_SERVICE_ACCOUNT_TOKEN}
      DATABASE_URL: ${DATABASE_URL}
      DJANGO_SETTINGS_MODULE: myproject.settings
    # Don't mount ~/.op in production
```

**3. Deploy**

```bash
export OP_SERVICE_ACCOUNT_TOKEN="ops_..."
docker compose -f docker-compose.prod.yml up -d

# Run migrations and create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web epicenv create-superuser
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

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Build and deploy
        env:
          OP_SERVICE_ACCOUNT_TOKEN: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          docker compose -f docker-compose.prod.yml build
          docker compose -f docker-compose.prod.yml up -d
          docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate
          docker compose -f docker-compose.prod.yml exec -T web epicenv create-superuser
```

Store `OP_SERVICE_ACCOUNT_TOKEN` in GitHub Secrets.

## How It Works

The `epicenv create-superuser` command uses a subprocess approach:

1. **Fetch credentials**: Runs on host (or in container with 1Password CLI access) using 1Password CLI
2. **Load environment**: Loads epicenv variables from pyproject.toml
3. **Execute Django**: Runs a Python subprocess with Django code to create/update the superuser
4. **Idempotent**: Safely creates new user or updates existing user's password

This design means:
- 1Password CLI must be available where epicenv runs
- Django must be installed in the Python environment
- Works identically in local and containerized environments

## Troubleshooting

### "1Password CLI is not available"

**Problem:** Container can't find the `op` command.

**Solutions:**

1. **Mount your 1Password session** (Approach 1):
   ```yaml
   volumes:
     - ~/.op:/root/.op:ro
   ```

2. **Install 1Password CLI in container** (Approach 2):
   ```dockerfile
   RUN curl -sSO https://downloads.1password.com/linux/debian/amd64/stable/1password-cli-amd64-latest.deb && \
       dpkg -i 1password-cli-amd64-latest.deb
   ```

3. **Verify installation**:
   ```bash
   docker compose exec web op --version
   ```

### "DJANGO_SETTINGS_MODULE not set"

**Problem:** Django can't find settings module.

**Solutions:**

1. **Set in docker-compose.yml**:
   ```yaml
   environment:
     DJANGO_SETTINGS_MODULE: myproject.settings
   ```

2. **Set in Dockerfile**:
   ```dockerfile
   ENV DJANGO_SETTINGS_MODULE=myproject.settings
   ```

3. **Use --settings flag**:
   ```bash
   docker compose exec web epicenv create-superuser --settings myproject.settings
   ```

### "Database connection failed"

**Problem:** Django can't connect to the database service.

**Solutions:**

1. **Check database is running:**
   ```bash
   docker compose ps
   ```

2. **Verify DATABASE_URL:**
   ```bash
   docker compose exec web env | grep DATABASE_URL
   ```

3. **Add health check:**
   ```yaml
   services:
     db:
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U myapp"]
         interval: 5s
         timeout: 5s
         retries: 5

     web:
       depends_on:
         db:
           condition: service_healthy
   ```

### "Session not found" or "Authentication required"

**Problem:** Container can't access your 1Password session.

**Solutions:**

1. **Sign in on host:**
   ```bash
   op signin
   ```

2. **Verify session mount:**
   Check that `~/.op:/root/.op:ro` is in your docker-compose.yml volumes.

3. **Check session in container:**
   ```bash
   docker compose exec web op vault list
   ```

4. **For production, use service account:**
   Set `OP_SERVICE_ACCOUNT_TOKEN` environment variable instead of mounting `~/.op`.

### "User table does not exist"

**Problem:** Migrations haven't been run.

**Solution:**
```bash
docker compose exec web python manage.py migrate
```

### Permission Issues with Mounted Volumes

**Problem:** Files created by container have wrong ownership.

**Solution:** Run container as your user:
```yaml
services:
  web:
    user: "${UID}:${GID}"
```

Set in your environment:
```bash
export UID=$(id -u)
export GID=$(id -g)
docker compose up
```

## Best Practices

1. **Use `docker compose exec` for running containers** - Faster than `docker compose run`

2. **Mount `~/.op` read-only** (`:ro` flag) to prevent accidental modifications

3. **Use service accounts in production** instead of personal 1Password sessions

4. **Run migrations before create-superuser** to ensure database tables exist

5. **Create setup scripts** to automate the development environment setup

6. **Don't commit .env files** - Use 1Password for all sensitive data

7. **Use health checks** in docker-compose.yml to ensure database is ready

## Related Documentation

- [create-superuser Command](create-superuser.md)
- [1Password Integration](1password.md)
- [Django Integration](django.md)
- [1Password Service Accounts](https://developer.1password.com/docs/service-accounts/)
