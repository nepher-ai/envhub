# Nepher: Universal Isaac Lab Environments Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-BUSL--1.1-blue.svg)](LICENSE)

**Nepher** is the Python package and `nepher` CLI for EnvHub, the Nepher catalogue of Isaac Lab simulation environments. It lets you discover, download, upload, cache and load environment bundles for any category (navigation, manipulation, humanoid, locomotion, ...), and turns a bundle's scenes into ready-to-use Isaac Lab configuration objects.

The same operations are also available as `npcli envhub ...` in the unified [nepher-cli](https://github.com/nepher-ai/nepher-cli). Both tools talk to the same API, share the same login and use the same local cache, so you can mix them freely.

## Concepts

An **environment** (env) is a versioned bundle of related simulation scenes. It has a unique ID, a category, a type (`usd` or `preset`), metadata, and one or more scenes. Bundles are described by a `manifest.yaml` at the root of the bundle.

A **scene** is one concrete simulation setup inside an environment:

- **USD scenes** reference a USD file, optionally with a ROS-style occupancy map used for collision-free spawn and goal sampling, and optionally a Python scene file that customises the configuration.
- **Preset scenes** are generated programmatically by a Python preset file in the bundle.

## Installation

```bash
pip install nepher
```

From source:

```bash
git clone https://github.com/nepher-ai/envhub.git
cd envhub
pip install -e .
```

Optional extras:

```bash
pip install -e ".[keyring]"    # store the API key in the system keyring
pip install -e ".[isaaclab]"   # Isaac Lab integration (needed for loading scenes and `view`)
pip install -e ".[dev]"        # pytest, black, ruff, mypy
```

Listing, downloading, uploading and cache management only need the base install. Loading scene configs and `nepher view` need Isaac Lab.

## Quick start

```bash
# Authenticate (you are prompted for the key, so it never lands in shell history)
nepher login
nepher whoami

# Discover environments
nepher list --category navigation
nepher list --search warehouse --json

# Download by ID (or by exact name) into the local cache
nepher download go2-maze-v0

# Inspect the cache
nepher cache list
nepher cache info

# List the scenes of a cached environment and open one in Isaac Sim
nepher view go2-maze-v0
nepher view go2-maze-v0 --scene 0
```

## Authentication

Get an API key at [nepher.ai/account](https://nepher.ai/account) under **Account → API Keys**. Keys start with `nepher_`.

```bash
nepher login                    # prompts for the key
nepher login --api-key nepher_… # non-interactive (key ends up in shell history)
nepher logout
```

`nepher login` stores the key only after `POST /api/v1/auth/api-key/login` succeeds. A rejected key or a connection failure prints the server or network error, including the URL that was called. Environment requests keep using the API key as `X-API-Key`.

Requests use the first key found in this order:

1. `--api-key` on the command (where supported) or the `NEPHER_API_KEY` environment variable
2. The key stored by `nepher login`
3. The key stored by `npcli login`
4. Keys written by `nepher` 0.1.x (read for backwards compatibility, removed on the next login or logout)

`nepher login` stores the key in the system keyring when the `keyring` extra is installed. Without it, the key goes in `~/.nepher/api_key`, readable only by your user. The key is never written to the config file.

`nepher logout` removes only the key stored by `nepher login`. If you also logged in with `npcli` or set `NEPHER_API_KEY`, that key keeps working; use `npcli logout` or unset the variable.

The key is sent on every request as `X-API-Key`, so long-running jobs such as validators keep working without refreshing tokens. A rotated key or a logout is picked up by the next request without restarting the process.

For CI and servers, set `NEPHER_API_KEY` instead of logging in.

## CLI reference

| Command | Description |
|---------|-------------|
| `nepher login` / `logout` / `whoami` | Manage and check authentication |
| `nepher list` | List environments. Filters: `--category`, `--type usd\|preset`, `--benchmark`, `--eval-benchmarks`, `--search`, `--limit`, `--json` |
| `nepher download ENV_ID` | Download and cache a bundle. Options: `--category`, `--cache-dir`, `--force`, `--api-key` |
| `nepher upload PATH` | Upload a bundle directory or `.zip`. Options: `--category` (required), `--benchmark`, `--force`, `--thumbnail`, `--api-key` |
| `nepher cache list` / `info` / `clear [ENV_ID]` / `migrate NEW_PATH` | Manage the local cache. All accept `--cache-dir` and `--category` |
| `nepher view ENV_ID` | List scenes, or open one in Isaac Sim with `--scene NAME_OR_INDEX` |
| `nepher config get` / `set` / `list` / `reset` | Manage configuration |

Every command exits with status 1 on failure, so it can be used in scripts.

`nepher download` first looks the argument up as an environment ID. Only when the server reports that ID does not exist does it search by exact name, and when several environments share that name it picks the most recently uploaded one. Authentication and network errors are reported as such and never trigger a name search.

`nepher upload` zips a directory automatically. Version-control folders, virtualenvs, `__pycache__`, `.pyc` files and `.env` files are left out of the archive.

### Viewing scenes in Isaac Sim

`nepher view` must run inside Isaac Lab's Python. Run it through the helper script:

```bash
# Linux / macOS
./isaaclab.sh -p /path/to/envhub/scripts/nepher_view.py go2-maze-v0 --scene 0 [--headless]

# Windows
isaaclab.bat -p C:\path\to\envhub\scripts\nepher_view.py go2-maze-v0 --scene 0
```

Isaac Lab launcher flags such as `--headless` or `--device` are forwarded to the app launcher. `npcli envhub view` works the same way and delegates to this package for rendering.

## Configuration

Settings are read from, highest priority first:

1. Command-line flags (for example `--cache-dir`)
2. Environment variables
3. The config file: `.nepherrc` in the current directory (TOML or JSON) if it exists, otherwise `~/.nepher/config.toml`
4. Built-in defaults

| Key | Default | Environment variable |
|-----|---------|----------------------|
| `api_url` | `https://api.nepher.ai/envhub` | `NEPHER_ENVHUB_API_URL`, then `ENVHUB_API_URL`, then `NEPHER_API_URL` + `/envhub` |
| `cache_dir` | `~/.nepher/cache` | `NEPHER_CACHE_DIR` |
| `categories.<name>.cache_dir` | unset (falls back to `cache_dir`) | none |
| `default_category` | unset | none |

```bash
nepher config set cache_dir /data/nepher-cache
nepher config set categories.manipulation.cache_dir /fast-ssd/manipulation
nepher config list
nepher config reset
```

Only values you set explicitly are written to the config file. `npcli envhub config` reads and writes the same file.

### Cache layout

Each environment is extracted to `<cache_dir>/<env_id>/` with its `manifest.yaml` at the root. Downloads go to a temporary file first and are extracted into a staging directory. The cache entry is replaced only when extraction completes and the manifest parses, so an interrupted or invalid download never shows up as cached, and a failed re-download keeps the previous copy.

`nepher cache clear` with no argument removes cached environments only, not other files in the cache directory. `nepher cache migrate NEW_PATH` moves the cached environments and saves `NEW_PATH` as the new `cache_dir` (or the category-specific one when `--category` is given).

## Bundle format

A bundle is a directory, or a `.zip` of one, with `manifest.yaml` at its root.

**USD environment**

```yaml
id: digital-twin-warehouse-v1
type: usd
version: 1.0.0
category: navigation
description: Digital twin of a small warehouse for navigation training

scenes:
  - scene_id: small_warehouse
    description: Small warehouse with realistic layout and obstacles
    usd: small_warehouse_digital_twin.usd
    omap_meta: digital_twin_omap/map.yaml   # optional ROS occupancy map
    scene: small_warehouse_scene.py         # optional Python scene config
```

**Preset environment**

```yaml
id: indoor-environments-v1
type: preset
version: 1.0.0
category: navigation
description: Indoor navigation environments

preset_scenes:
  - scene_id: hospital
    description: Hospital corridor environment
    preset: hospital_preset.py
  - scene_id: warehouse
    description: Warehouse with shelves and bounding walls
    preset: warehouse_preset.py
```

All paths in the manifest (`usd`, `omap_meta`, `scene`, `preset`) are relative to the bundle root and must stay inside the bundle. Absolute paths and paths that climb out with `..` are rejected: archive members when the bundle is extracted, `usd` and `omap_meta` when the manifest is parsed, and `scene` and `preset` when the scene is loaded. Loaded configs receive absolute paths into the cache.

When a scene has an occupancy map, that map determines where robots and goals may be placed, and `spawn_areas` / `exclusion_zones` from the scene config are not applied. Without a map, each spawn area is sampled separately according to its `weight`, so the gaps between areas are never used. If the map frame does not line up with the USD scene origin, set `occupancy_map_offset = (x, y, yaw)` on the scene config.

> **Security note:** preset files and Python scene files run as ordinary Python code when a scene is loaded or viewed. Only load bundles from authors you trust.

## Python API

```python
from nepher import load_env, load_scene

env = load_env("indoor-environments-v1", category="navigation")
print([s.name for s in env.get_all_scenes()])   # ['hospital', 'warehouse']

scene_cfg = load_scene(env, scene="hospital")   # name or index
# Use scene_cfg with your Isaac Lab environment configuration.
```

`load_env` looks in the configured cache (or `cache_dir=...`) and falls back to an `environments/` directory next to the package for locally developed bundles. It does not download; run `nepher download` first.

The API client is available too:

```python
from nepher import get_client

client = get_client()                  # uses the stored or NEPHER_API_KEY credentials
envs = client.list_environments(category="navigation", limit=10)
```

## Upgrading from 0.1.x

- The default API URL is now `https://api.nepher.ai/envhub`, the same as `npcli`. A config file that still contains the old default (`https://envhub-api.nepher.ai`) is treated as unset. Any other `api_url` you configured is kept.
- API keys are no longer stored in `config.toml` or base64-encoded in `api_key.enc`. Old keys are still read, and are moved to the new storage on the next `nepher login`.
- `nepher login` checks the key against EnvHub and requires the `nepher_` prefix.
- API-key management (create, list, revoke) has moved to the account service: use `npcli account api-keys`.
- Commands exit with status 1 on failure (previously 0).
- `nepher download` no longer substring-matches names, and no longer falls back to a search on auth or network errors.
- Occupancy maps given in the manifest (`omap_meta`) or as a relative path in a scene file are now used for spawn sampling. Previously they were set after the sampler was built and silently ignored. Configs with several spawn areas now sample each area instead of the bounding box around all of them. Both change spawn distributions for affected scenes.

## Development

```bash
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Business Source License 1.1 (BUSL-1.1). See [LICENSE](LICENSE).
