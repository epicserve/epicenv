# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.6.1] - 2026-05-22

### Fixed
- `epicenv create-superuser` now reads piped stdin reliably regardless of upstream producer timing. The previous zero-timeout `select.select()` check raced against the producer half of a bash pipeline and silently dropped any input that took more than a few microseconds to arrive, breaking realistic invocations like `op item get ... | epicenv create-superuser` and `vault kv get ... | epicenv create-superuser`. The CLI now blocks on a full stdin read (gated by `isatty()` so interactive use still works) until the producer closes the pipe.


## [1.6.0] - 2026-05-22

### Added
- Python 3.14 added to the CI test matrix and to the supported-versions classifiers in `pyproject.toml`
- `epicenv secrets get <reference>` command — retrieve secrets from 1Password (and future providers) with `--fields`, `--format json|env|plain`, and `--silent` flags
- `epicenv create-superuser` command — idempotent Django superuser creation that auto-detects credentials from stdin (piped JSON), `DJANGO_SUPERUSER_*` environment variables, or explicit `--username/--email/--password` flags; supports `--force` to update an existing user
- `epicenv.secrets` module with `SecretProvider` abstract base class and `OnePasswordProvider` implementation, enabling future providers (AWS Secrets Manager, Vault, etc.)
- `epicenv.frameworks` module with `FrameworkIntegration` abstract base class for future framework integrations
- Auto-detection of `DJANGO_SETTINGS_MODULE` from environment or `[tool.epicenv.django] settings_module` in `pyproject.toml`
- [Field Mapping Guide](docs/field-mapping.md) — patterns for transforming secrets with `jq` between `epicenv secrets get` and consuming commands

### Changed
- 1Password CLI integration refactored into the new `epicenv.secrets.onepassword` module; the public `onepassword()` initializer in `epicenv.initializers` keeps the same signature and behavior


## [1.5.0] - 2026-05-22

### Added
- `--min` flag for `epicenv create` that generates a `.env` with only required variables (those without defaults) and no per-variable help text. The header still explains what was generated, how to run `epicenv create` for the full version, and points at the schema file (`.env.toml` or `pyproject.toml`) where variable documentation lives.


## [1.4.0]

### Changed
- Minimum supported `environs` version bumped from `>=11.0.0` to `>=14.0.0` to match what's actually exercised by CI and the lockfile
- CI now runs the test suite against both `environs==14.2.0` and `environs==15.0.1` across Python 3.11, 3.12, and 3.13

### Notes for users on environs 15+
- `environs` 15.0.0 changed `Env.read_env()` to no longer mutate `os.environ` — parsed values now live on the `environs.Env` instance only. epicenv passes this behavior through unchanged. If your project calls `env.read_env(".env")` and then reads `os.environ["VAR"]` directly, switch to the typed accessor (`env.str("VAR")`, `env.bool("VAR")`, etc.) when upgrading to `environs>=15`.


## [1.3.0] - 2026-05-14

### Added
- Schema can now live in a dedicated `.env.toml` file next to `pyproject.toml` (auto-discovered) or at a custom path via `[tool.epicenv] config_file = "..."` in `pyproject.toml`
- `ConfigError` exception raised when schema is defined in both `pyproject.toml` and an external file, or when `config_file` points to a missing path
- `get_schema_path()` helper in `epicenv._config` returns the resolved schema file location

### Changed
- CLI commands (`create`, `diff`, `validate`) now report the actual schema file path in use rather than always showing `pyproject.toml`


## [1.2.0] - 2026-01-25

### Added
- 1Password CLI initializer (`onepassword`) for secure password generation and management
- Refactored initializers into dedicated `epicenv.initializers` module


## [1.1.0] - 2025-01-25

### Added
- Built-in initializers module with `url_safe_password` function
- Support for `args` and `kwargs` parameters in `initial_func` schema field

### Changed
- Schema defaults in `pyproject.toml` are now only used for `.env` file generation and diff commands, not at runtime
- Runtime defaults must be specified in Python code (e.g., `env.bool("DEBUG", default=False)`)


## [1.0.0] - 2025-01-24

### Added
- Schema-based environment variable management via `pyproject.toml`
- CLI commands: `epicenv create`, `epicenv diff`, `epicenv validate`
- Validation mode controlled by `EPICENV_VALIDATE` environment variable
- Full type support for all environs types (str, bool, int, list, url, json, etc.)
- Django integration with `dj_db_url`, `dj_email_url`, `dj_cache_url` support
- Support for `initial_func` to generate dynamic initial values

### Changed
- Renamed package from `envutil` to `epicenv` (PyPI name conflict)
- Complete rewrite with schema-first approach
