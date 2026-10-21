<div align="center">

# 🌐 Nepher EnvHub

**Discover, share and load Isaac Lab simulation environments with one command.**

[![PyPI](https://img.shields.io/pypi/v/nepher?color=blue)](https://pypi.org/project/nepher/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Isaac Lab](https://img.shields.io/badge/Isaac%20Lab-ready-76B900.svg)](https://isaac-sim.github.io/IsaacLab/)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)

[Quick start](#-quick-start) •
[CLI](#-cli) •
[Python API](#-python-api) •
[Bundle format](#-bundle-format) •
[Configuration](#%EF%B8%8F-configuration)

</div>

---

`nepher` is the Python package and CLI for **EnvHub**, the Nepher catalogue of Isaac Lab environments. It downloads, caches and uploads environment bundles for any category (navigation, manipulation, locomotion, humanoid, ...) and turns their scenes into ready-to-use Isaac Lab configs.

> [!TIP]
> Prefer one tool for everything? The same commands are available as `npcli envhub ...` in [nepher-cli](https://github.com/nepher-ai/nepher-cli). Both share the same login, API and cache.

## ✨ Concepts

| | |
|---|---|
| **Environment** | A versioned bundle of related scenes, described by a `manifest.yaml`. Type is `usd` or `preset`. |
| **USD scene** | USD assets plus their scene configuration: placement and scale, terrain physics, lighting and sky, spawn areas, and an optional occupancy map. |
| **Preset scene** | A scene generated programmatically by a Python preset file. |

## 📦 Installation

```bash
pip install nepher                 # core: list, download, upload, cache
pip install "nepher[isaaclab]"     # + load scenes and `nepher view`
pip install "nepher[keyring]"      # + store the API key in the system keyring
```

## 🚀 Quick start

```bash
nepher login                              # paste your key from nepher.ai/account
nepher list --category navigation         # browse environments
nepher download go2-maze-v0               # fetch into the local cache
nepher view go2-maze-v0 --scene 0         # open a scene in Isaac Sim
```

```python
from nepher import load_env, load_scene

env = load_env("go2-maze-v0", category="navigation")
scene_cfg = load_scene(env, scene=0)      # plug into your Isaac Lab env config
```

## 🧰 CLI

| Command | What it does |
|---|---|
| `nepher login` · `logout` · `whoami` | Manage authentication |
| `nepher list` | List environments (`--category`, `--type`, `--search`, `--benchmark`, `--limit`, `--json`) |
| `nepher download ENV_ID` | Download and cache a bundle by ID or exact name (`--force`, `--cache-dir`) |
| `nepher upload PATH` | Upload a bundle folder or `.zip` (`--category` required, `--thumbnail`, `--benchmark`) |
| `nepher view ENV_ID` | List scenes, or open one in Isaac Sim with `--scene NAME_OR_INDEX` |
| `nepher cache` `list` · `info` · `clear` · `migrate` | Manage the local cache |
| `nepher config` `get` · `set` · `list` · `reset` | Manage settings |

All commands exit with status `1` on failure, so they are safe to use in scripts.

<details>
<summary><b>Running <code>nepher view</code> inside Isaac Lab</b></summary>

`view` needs Isaac Lab's Python, so launch it through the helper script. Launcher flags such as `--headless` and `--device` are forwarded.

```bash
./isaaclab.sh -p /path/to/envhub/scripts/nepher_view.py go2-maze-v0 --scene 0     # Linux / macOS
isaaclab.bat -p C:\path\to\envhub\scripts\nepher_view.py go2-maze-v0 --scene 0    # Windows
```

</details>

## 🔑 Authentication

Create an API key at [nepher.ai/account](https://nepher.ai/account) → **API Keys** (keys start with `nepher_`). The first key found wins:

1. `--api-key` flag or the `NEPHER_API_KEY` environment variable (recommended for CI)
2. The key saved by `nepher login` (system keyring, or `~/.nepher/api_key`)
3. The key saved by `npcli login`

## 🐍 Python API

```python
from nepher import get_client, load_env, load_scene

env = load_env("indoor-environments-v1", category="navigation")
print([s.name for s in env.get_all_scenes()])    # ['hospital', 'warehouse']
scene_cfg = load_scene(env, scene="hospital")

client = get_client()
envs = client.list_environments(category="navigation", limit=10)
```

`load_env` reads from the local cache only; run `nepher download` first.

## 📁 Bundle format

A bundle is a folder (or `.zip`) with a `manifest.yaml` at its root. All paths are relative to the bundle and may not escape it.

<table>
<tr><th>USD environment</th><th>Preset environment</th></tr>
<tr><td>

```yaml
id: digital-twin-warehouse-v1
type: usd
version: 1.0.0
category: navigation
scenes:
  - scene_id: small_warehouse
    usd: warehouse.usd
    omap_meta: omap/map.yaml  # optional
    scene: warehouse_scene.py # optional
```

</td><td>

```yaml
id: indoor-environments-v1
type: preset
version: 1.0.0
category: navigation
preset_scenes:
  - scene_id: hospital
    preset: hospital_preset.py
  - scene_id: warehouse
    preset: warehouse_preset.py
```

</td></tr>
</table>

The optional scene file configures how the USD assets are used in simulation: transform and scale, terrain friction, lighting and sky, spawn areas and exclusion zones. When an occupancy map is provided, it decides where robots and goals spawn.

> [!WARNING]
> Preset and scene files are executed as Python when loaded. Only load bundles from authors you trust.

## ⚙️ Configuration

Priority: CLI flags → environment variables → `.nepherrc` (project) or `~/.nepher/config.toml` → defaults.

| Key | Default | Env variable |
|---|---|---|
| `api_url` | `https://api.nepher.ai/envhub` | `NEPHER_ENVHUB_API_URL` |
| `cache_dir` | `~/.nepher/cache` | `NEPHER_CACHE_DIR` |
| `categories.<name>.cache_dir` | falls back to `cache_dir` | — |
| `default_category` | unset | — |

```bash
nepher config set cache_dir /data/nepher-cache
nepher config set categories.manipulation.cache_dir /fast-ssd/manipulation
```

Downloads are atomic: an interrupted or invalid download never replaces a good cached copy.

## 🤝 Contributing

```bash
git clone https://github.com/nepher-ai/envhub.git && cd envhub
pip install -e ".[dev]" && pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Released under the [BSD 3-Clause License](LICENSE).
