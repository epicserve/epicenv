# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


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
