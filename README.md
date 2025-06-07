# Django Envtools

A Django package that enhances the [environs](https://github.com/sloria/environs) library by adding management commands to simplify environment variable handling.

## Management Commands
- `create_env_file`: Creates a new `.env` file with default values, help text, and initial value hooks for environment variables.
- `diff_env_file`: Displays differences between your `.env` file and the environment variables in your Django settings.

## Installation

Install via `uv` or `pip`:

```bash
uv add django-envtools

# or

pip install django-envtools
```

## Usage

First, add `django_envtools` to your `INSTALLED_APPS` in `settings.py`:

```python  
INSTALLED_APPS = [
    ...
    'django_envtools',
]
```

Then, update your settings to use the `Env` class to read environment variables. Django Envtools adds three keyword
arguments that `environs` doesn't have: `help_text`, `initial_func`, and `initial`.

* `help_text`: Provides help text for each environment variable.
* `initial_func`: A callable or a string path to a callable that generates an initial value when runing the
   `create_env_file` management command.
* `initial`: Set an initial value for environment variable when running the `create_env_file` management command. If
  `initial_func` is provided, this value will be ignored.

For example, if you have the following in your `settings.py`:

```python
from pathlib import Path
from django_envtools import Env

BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environs and load environment variables from .env file
env = Env()
env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str(
    "SECRET_KEY",
    initial_func="django.core.management.utils.get_random_secret_key",
    help_text="Django's secret key, see https://docs.djangoproject.com/en/dev/ref/settings/#secret-key for more information",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False, initial="on", help_text="Set to `on` to enable debugging")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[],
    help_text="List of allowed hosts (e.g., `127.0.0.1,example.com`), see https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts for more information",
)

DATABASES = {
    "default": env.dj_db_url(
        "DATABASE_URL",
        default="sqlite:///db.sqlite3",
        help_text="Database URL, see https://github.com/jazzband/dj-database-url for more information",
    )
}

# See https://github.com/migonzalvar/dj-email-url for more examples on how to set the EMAIL_URL
email = env.dj_email_url(
    "EMAIL_URL",
    default="smtp://skroob@planetspaceball.com:12345@smtp.planetspaceball.com:587/?ssl=True&_default_from_email=President%20Skroob%20%3Cskroob@planetspaceball.com%3E",
    help_text="See https://github.com/migonzalvar/dj-email-url for more examples on how to set the EMAIL_URL",
)
DEFAULT_FROM_EMAIL = email["DEFAULT_FROM_EMAIL"]
EMAIL_HOST = email["EMAIL_HOST"]
EMAIL_PORT = email["EMAIL_PORT"]
EMAIL_HOST_PASSWORD = email["EMAIL_HOST_PASSWORD"]
EMAIL_HOST_USER = email["EMAIL_HOST_USER"]
EMAIL_USE_TLS = email["EMAIL_USE_TLS"]
```

After setting up, you can run the management command `./manage.py create_env_file` to generate a `.env` file with the
following content:

```bash
# This is an initial .env file generated on 2024-10-31T19:21:56.174711+00:00. Any environment variable with a default
# can be safely removed or commented out. Any variable without a default must be set.

# Django's secret key, see https://docs.djangoproject.com/en/dev/ref/settings/#secret-key for more information
# type: str
SECRET_KEY=redacted-secret-key

# Set to `on` to enable debugging
# type: bool
# default: False
# DEBUG=

# List of allowed hosts (e.g., `127.0.0.1,example.com`), see https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts for more information
# type: list
# default: []
# ALLOWED_HOSTS=

# Database URL, see https://github.com/jazzband/dj-database-url for more information
# type: dj_db_url
# default: sqlite:///db.sqlite3
# DATABASE_URL=

# See https://github.com/migonzalvar/dj-email-url for more examples on how to set the EMAIL_URL
# type: dj_email_url
# default: smtp://skroob@planetspaceball.com:12345@smtp.planetspaceball.com:587/?ssl=True&_default_from_email=President%20Skroob%20%3Cskroob@planetspaceball.com%3E
# EMAIL_URL=
```

As the project grows, you can run `./manage.py diff_env_file` to identify differences between your `.env` file and
`settings.py`, helping you spot missing or orphaned environment variables.

An example output might look like:

```bash
Environment variables missing in .env file:
- ALLOWED_HOSTS
- DEBUG

Environment variables missing in .env file with default values:
- DATABASE_URL

Environment variables in .env file that are not defined in your Django settings:
- FOO
- BAR
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request. If you have any questions, feel free to
reach out.

## License
This project is licensed under the MIT License.
