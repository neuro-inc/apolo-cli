# AGENTS.md
## Overview

This is a monorepo for the **Apolo Platform** client (ML/AI platform). It contains two Python packages that are always released together at the same version:

- **`apolo-sdk/`** — async Python SDK (`apolo_sdk`) built on `aiohttp` for communicating with the Apolo platform services APIs.
- **`apolo-cli/`** — `click`-based CLI tool (`apolo` commands) that wraps the SDK.

## Development Commands
### Setup
```bash
make setup        # install dev deps + pre-commit hooks
```

### Format & Lint
```bash
make format       # pre-commit run --all-files (black, isort, flake8, pyupgrade, yesqa)
make lint         # format + mypy on both packages
```

### Tests
```bash
make test-sdk     # pytest unit tests for apolo-sdk
make test-cli     # pytest unit tests for apolo-cli
make test-all     # both
make e2e          # end-to-end tests (requires live platform E2E_TOKEN env var)
```

### Running a single test
```bash
pytest apolo-cli/tests/unit/test_job.py::test_function_name -v
pytest apolo-sdk/tests/test_jobs.py::TestClassName::test_method -v
```

Pytest is configured in `setup.cfg` (`[tool:pytest]`). The `asyncio_mode = auto` setting means async test functions are automatically run with asyncio. Test markers: `e2e`, `e2e_job`, `require_admin`, `xdist_group`.

### Formatter snapshot tests
CLI output is tested against ASCII reference files under `apolo-cli/tests/unit/formatters/`. To regenerate them after intentional output changes:
```bash
pytest --rich-gen apolo-cli/tests/unit/formatters/
```

### Changelog
```bash
towncrier create <issue-num>.(bugfix|feature|doc|removal|misc) --edit
```

## Architecture

### SDK (`apolo_sdk`)

The `Client` class (`apolo-sdk/src/apolo_sdk/_client.py`) is the SDK facade. It is created via `Factory` (`_config_factory.py`) and is a composition of service objects:

| `client.<attr>` | Module | Responsibility |
|---|---|---|
| `jobs` | `_jobs.py` | Job lifecycle: run, list, status, exec, logs, kill, top |
| `storage` | `_storage.py` | Remote filesystem: ls, cp, mkdir, rm, mv |
| `images` | `_images.py` | Docker image push/pull/list via platform registry |
| `secrets` | `_secrets.py` | Secret CRUD |
| `disks` | `_disks.py` | Persistent disk (block storage) management |
| `buckets` | `_buckets.py` | Object storage (S3-like/GCS/Azure providers) |
| `apps` | `_apps.py` | Application deployment and lifecycle |
| `config` | `_config.py` | Auth config, cluster config, presets |
| `parse` | `_parser.py` | URI/volume/image string parsing |

**Transport layer**: `_Core` (`_core.py`) wraps `aiohttp.ClientSession`, manages Bearer token auth, SQLite cookie caching, HTTP error → exception mapping, and tracing.

**Auth**: OAuth2 PKCE flow (`_login.py`). Config stored at `~/.apolo/` (TOML-like files + SQLite for cookies). Override path with `APOLO_CONFIG` env var.

**Plugin system**: `PluginManager` / `ConfigBuilder` allow third-party plugins to register config parameters and version checkers via the `apolo_api` entry point group.

**Bucket providers**: Separate files for aiobotocore/S3 (`_s3_bucket_provider.py`), google-auth/GCS (`_gcs_bucket_provider.py`), and azure-storage-blob (`_azure_bucket_provider.py`).

### CLI (`apolo_cli`)

Entry point: `apolo_cli.main:main`. The CLI uses Click with a custom `MainGroup` that lazy-loads command modules via `CMD_MAP` in `main.py`.

**Command modules** (each = one Click group): `job.py`, `storage.py`, `image.py`, `config.py`, `admin.py`, `blob_storage.py`, `secrets.py`, `disks.py`, `apps.py`, `vcluster.py`, `share.py`, `alias.py`, `completion.py`, `topics.py`.

**`utils.py`**: Core decorator wrappers (`@command`, `@group`, `@option`, `@argument`) that add the `init_client` flag, auto-wrap async handlers, and handle stats upload.

**`formatters/`**: Each resource type has a formatter module using `rich` tables/text. Unit tests compare output against `.ref` ASCII snapshot files via the `rich_cmp` pytest fixture.

**`click_types.py`**: Custom Click parameter types with shell completers for job IDs, presets, clusters, etc. Update `test_shell_completion.py` when adding new commands.

### Import Order
isort sections (in order): `FUTURE`, `STDLIB`, `THIRDPARTY`, `APOLOSDK`, `FIRSTPARTY`, `TESTS`, `LOCALFOLDER`.

## Key Files

| File | Purpose |
|---|---|
| `apolo-cli/src/apolo_cli/main.py` | CLI entry point, `CMD_MAP`, `MainGroup` |
| `apolo-cli/src/apolo_cli/root.py` | `Root` dataclass (per-invocation state) |
| `apolo-cli/src/apolo_cli/utils.py` | `@command`/`@group` decorators, async runner |
| `apolo-sdk/src/apolo_sdk/_client.py` | `Client` class (SDK facade) |
| `apolo-sdk/src/apolo_sdk/_core.py` | `_Core` HTTP transport layer |
| `apolo-sdk/src/apolo_sdk/_config_factory.py` | `Factory`, config loading, auth flow |
| `apolo-sdk/src/apolo_sdk/__init__.py` | Full public SDK API surface |
| `apolo-cli/tests/unit/conftest.py` | CLI unit test fixtures (`run_cli`, `root`, `rich_cmp`) |
| `apolo-cli/tests/conftest.py` | Shared fixtures (`make_client`, cluster config) |
| `setup.cfg` | Root-level pytest/flake8/isort/mypy config |
| `Makefile` | All development commands |

## Development guide
- Always run `make format` and `make test-{package}` before committing after changes.
- Do not run `make e2e` locally — e2e tests are run by CI in PRs.
- `CLI.md` is auto-generated by the `gen-cli-docs` pre-commit hook (`make docs`). Do not edit it directly; update command docstrings or source templates instead.
- This is a published SDK — write code compatible with the minimum supported Python version (currently it's 3.10). Update this if version changes.
