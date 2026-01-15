# Quick Start Guide

## Installation

```bash
pip install nepher
```

Or install from source:

```bash
git clone https://github.com/nepher_ai/envhub.git
cd envhub
pip install -e .
```

## Basic Usage

### 1. Authenticate

```bash
nepher login <your_api_key>
```

### 1.1. Check Authentication Status

```bash
# Show current user information
nepher whoami
```

### 2. List Environments

```bash
# List all environments
nepher list

# Filter by category
nepher list --category navigation

# Filter by type
nepher list --type usd

# Search
nepher list --search "indoor"
```

### 3. Download Environment

```bash
nepher download <env_id> --category navigation
```

### 4. Upload Environment

```bash
nepher upload ./my-env.zip --category manipulation --thumbnail ./thumbnail.png
```

### 5. Manage Cache

```bash
# List cached environments
nepher cache list

# Clear cache
nepher cache clear

# Get cache info
nepher cache info
```

### 6. View Environment

```bash
# View an environment in Isaac Sim
nepher view <env_id> --category navigation

# View a specific scene
nepher view <env_id> --category navigation --scene <scene_name>
```

**Note:** The `view` command requires Isaac Lab to be installed. If Isaac Lab is not available in your current environment, use the script instead:
```bash
isaaclab.bat -p scripts/nepher_view.py <env_id> --category navigation [--scene <scene>]
```

### 7. Configure

```bash
# Set cache directory
nepher config set cache_dir /custom/path

# Get config value
nepher config get cache_dir

# List all config
nepher config list
```

## Python API

```python
import nepher

# Authenticate
nepher.login("your_api_key")

# List environments
envs = nepher.list_environments(category="navigation")

# Download environment
nepher.download("env-id", category="navigation")

# Load environment
env = nepher.load_env("env-id", category="navigation")
scene = nepher.load_scene(env, scene="scene-name", category="navigation")
```

## Next Steps

- See [README.md](README.md) for more details

