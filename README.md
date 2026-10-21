<div align="center">

# Nepher EnvHub

**Discover, share and load Isaac Lab simulation environments, by [Nepher Robotics](https://nepher.ai).**

[![PyPI](https://img.shields.io/pypi/v/nepher)](https://pypi.org/project/nepher/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Isaac Lab](https://img.shields.io/badge/Isaac%20Lab-ready-76B900.svg)](https://isaac-sim.github.io/IsaacLab/)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)

[Install](#install) •
[Quick start](#quick-start) •
[CLI](#cli) •
[Python API](#python-api) •
[Bundle format](docs/bundle-format.md) •
[Configuration](#configuration)

</div>

---

`nepher` is the Python package and CLI for EnvHub, the Nepher catalogue of Isaac Lab environments. It downloads, caches and uploads environment bundles for any category (navigation, manipulation, locomotion, humanoid, ...) and turns their scenes into ready-to-use Isaac Lab configs.

The same commands are also available as `npcli envhub ...` in [nepher-cli](https://github.com/nepher-ai/nepher-cli). Both share the same login, API and cache.

## Concepts

| Term | Meaning |
|---|---|
| Environment | A versioned bundle of related scenes, described by a `manifest.yaml`. Type is `usd` or `preset`. |
| USD scene | USD assets plus their scene configuration: placement and scale, terrain physics, lighting and sky, spawn areas, and an optional occupancy map. |
| Preset scene | A scene generated programmatically by a Python preset file. |

## Install

```bash
pip install nepher                  # list, download, upload, cache
pip install "nepher[isaaclab]"      # adds scene loading and `nepher view`
pip install "nepher[keyring]"       # stores the API key in the system keyring
```

## Quick start

```bash
nepher login
nepher list --category navigation
nepher download go2-maze-v0
nepher view go2-maze-v0 --scene 0
```

Get your API key at [nepher.ai/account](https://nepher.ai/account) under **API Keys**. In CI, set `NEPHER_API_KEY` instead of logging in.

## CLI

| Command | Description |
|---|---|
| `nepher login` / `logout` / `whoami` | Manage authentication |
| `nepher list` | List environments |
| `nepher download ENV_ID` | Download and cache a bundle by ID or exact name |
| `nepher upload PATH` | Upload a bundle folder or `.zip` |
| `nepher view ENV_ID` | List scenes, or open one in Isaac Sim |
| `nepher cache list` / `info` / `clear` / `migrate` | Manage the local cache |
| `nepher config get` / `set` / `list` / `reset` | Manage settings |

All commands exit with status `1` on failure. Run any command with `--help` for all options.

<details>
<summary>Common options</summary>

| Command | Options |
|---|---|
| `list` | `--category`, `--type usd\|preset`, `--search`, `--benchmark`, `--eval-benchmarks`, `--limit`, `--json` |
| `download` | `--category`, `--cache-dir`, `--force`, `--api-key` |
| `upload` | `--category` (required), `--benchmark`, `--thumbnail`, `--force`, `--api-key` |
| `view` | `--scene NAME_OR_INDEX` |
| `cache` | `--cache-dir`, `--category` |

</details>

<details>
<summary>Running <code>nepher view</code> inside Isaac Lab</summary>

`view` needs Isaac Lab's Python, so launch it through the helper script. Launcher flags such as `--headless` and `--device` are forwarded.

```bash
./isaaclab.sh -p /path/to/envhub/scripts/nepher_view.py go2-maze-v0 --scene 0     # Linux / macOS
isaaclab.bat -p C:\path\to\envhub\scripts\nepher_view.py go2-maze-v0 --scene 0    # Windows
```

</details>

## Python API

```python
from nepher import get_client, load_env, load_scene

env = load_env("indoor-environments-v1", category="navigation")
print([s.name for s in env.get_all_scenes()])    # ['hospital', 'warehouse']
scene_cfg = load_scene(env, scene="hospital")    # use in your Isaac Lab env config

client = get_client()
envs = client.list_environments(category="navigation", limit=10)
```

`load_env` reads from the local cache only, so run `nepher download` first.

Publishing your own environments? See the [bundle format guide](docs/bundle-format.md). Bundles contain Python scene files that run when loaded, so only load bundles from authors you trust.

## Configuration

Settings are resolved in this order: CLI flags, environment variables, the config file (`.nepherrc` in the project or `~/.nepher/config.toml`), then defaults.

| Key | Default | Environment variable |
|---|---|---|
| `api_url` | `https://api.nepher.ai/envhub` | `NEPHER_ENVHUB_API_URL` |
| `cache_dir` | `~/.nepher/cache` | `NEPHER_CACHE_DIR` |
| `categories.<name>.cache_dir` | falls back to `cache_dir` | |
| `default_category` | unset | |

```bash
nepher config set cache_dir /data/nepher-cache
nepher config set categories.manipulation.cache_dir /fast-ssd/manipulation
```

API keys are resolved from `--api-key` or `NEPHER_API_KEY` first, then the key saved by `nepher login`, then the one saved by `npcli login`.

## Contributing

```bash
git clone https://github.com/nepher-ai/envhub.git && cd envhub
pip install -e ".[dev]" && pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[BSD 3-Clause](LICENSE) © 2026 Nepher Robotics
