# Nepher Commands Guide

Complete reference guide for using the Nepher CLI and Python API.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Authentication](#authentication)
4. [Environment Management](#environment-management)
5. [Cache Management](#cache-management)
6. [Viewing Environments](#viewing-environments)
7. [Python API](#python-api)
8. [Workflow Examples](#workflow-examples)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Install from Source

```bash
# Clone the repository
git clone <repository-url>
cd envhub

# Install in development mode
pip install -e .

# Or install in production mode
pip install .
```

### Verify Installation

```bash
# Check version
nepher --version

# Get help
nepher --help
```

---

## Configuration

### View Current Configuration

```bash
# List all configuration values
nepher config list

# Get specific configuration value
nepher config get cache_dir
nepher config get api_url
nepher config get default_category
```

### Set Configuration Values

```bash
# Set cache directory
nepher config set cache_dir /path/to/cache

# Set API URL
nepher config set api_url https://api.envhub.example.com

# Set default category
nepher config set default_category navigation

# Set category-specific cache directory
nepher config set categories.navigation.cache_dir /custom/nav/cache
```

### Reset Configuration

```bash
# Reset to default values
nepher config reset
```

### Environment Variables

You can also configure Nepher using environment variables:

```bash
# Set API key
export NEPHER_API_KEY="envhub_..."

# Set API URL
export NEPHER_API_URL="https://api.envhub.example.com"

# Set cache directory
export NEPHER_CACHE_DIR="/custom/cache/path"
```

**Configuration Priority (highest to lowest):**
1. CLI arguments (e.g., `--cache-dir` flag)
2. Environment variables (`NEPHER_*`)
3. Config file (`~/.nepher/config.toml`)
4. Category-specific overrides
5. Default values

---

## Authentication

### Login

```bash
# Login with API key
nepher login envhub_your_api_key_here
```

The API key is stored securely in your configuration directory (`~/.nepher/`).

### Check Authentication Status

```bash
# Show current user information
nepher whoami
```

Output example:
```
Current user:
  Username: john_doe
  Email: john@example.com
  Role: contributor
  Status: Active
```

### Logout

```bash
# Clear stored credentials
nepher logout
```

---

## Environment Management

### List Environments

```bash
# List all environments
nepher list

# Filter by category
nepher list --category navigation
nepher list --category manipulation

# Filter by type
nepher list --type usd
nepher list --type preset

# List only benchmark environments
nepher list --benchmark

# Search environments
nepher list --search "warehouse"

# Limit number of results
nepher list --limit 10

# Output as JSON
nepher list --json

# Combine filters
nepher list --category navigation --type usd --benchmark
```

**Available Environments (examples from `environments/` folder):**

- **digital-twin-warehouse-v1** (USD, navigation) - Digital twin warehouse with realistic layout
- **indoor-environments-v1** (preset, navigation) - Hospital and warehouse indoor scenes
- **outdoor-environments-v1** (preset, navigation) - Park and urban street outdoor scenes
- **usd-small-warehouse** (USD, navigation) - Small warehouse USD environment
- **waypoint-benchmark-v1** (preset, navigation, benchmark) - Waypoint benchmark with basic ground
- **waypoint-sample-v1** (preset, navigation) - Waypoint sample with basic ground

### Download Environments

```bash
# Download an environment (required: --category)
nepher download indoor-environments-v1 --category navigation
nepher download digital-twin-warehouse-v1 --category navigation
nepher download outdoor-environments-v1 --category navigation
nepher download waypoint-benchmark-v1 --category navigation

# Force re-download (overwrite existing cache)
nepher download indoor-environments-v1 --category navigation --force

# Download to custom cache directory
nepher download indoor-environments-v1 --category navigation --cache-dir /tmp/cache
```

### Upload Environments

```bash
# Upload an environment bundle (required: --category)
nepher upload ./environments/digital-twin-warehouse-v1 --category navigation
nepher upload ./environments/indoor-environments-v1 --category navigation
nepher upload ./environments/outdoor-environments-v1 --category navigation

# Upload as benchmark environment
nepher upload ./environments/waypoint-benchmark-v1 --category navigation --benchmark

# Force upload even if duplicate exists
nepher upload ./environments/usd-small-warehouse --category navigation --force

# Upload with thumbnail
nepher upload ./environments/digital-twin-warehouse-v1 --category navigation --thumbnail ./environments/digital-twin-warehouse-v1/thumbnail.png

nepher upload ./environments/indoor-environments-v1 --category navigation --thumbnail ./environments/indoor-environments-v1/thumbnail.png 
nepher upload ./environments/waypoint-benchmark-v1 --category navigation --thumbnail ./environments/waypoint-benchmark-v1/thumbnail.png --benchmark


```

**Environment Bundle Structure:**

Your environment bundle should have this structure:

**For USD environments:**
```
my-usd-environment/
├── manifest.yaml          # Required: Environment manifest
├── scene1.usd            # USD scene files
├── scene2.usd
├── omap/                 # Optional: Occupancy maps
│   ├── map.png
│   └── map.yaml
├── Materials/            # Optional: Material assets
└── ...                   # Other assets
```

**For Preset environments:**
```
my-preset-environment/
├── manifest.yaml          # Required: Environment manifest
├── scene1_preset.py      # Preset scene files
├── scene2_preset.py
├── thumbnail.png         # Optional: Thumbnail image
└── ...                   # Other assets
```

**Example manifest.yaml for USD environment:**
```yaml
id: digital-twin-warehouse-v1
type: usd
version: 1.0.0
description: Digital twin of a small warehouse environment for navigation training
category: navigation

scenes:
  - scene_id: small_warehouse
    description: Small warehouse digital twin with realistic layout and obstacles
    usd: small_warehouse_digital_twin.usd
    omap_image: digital_twin_omap/map.png
    omap_meta: digital_twin_omap/map.yaml
    # Optional: Python scene file for custom configuration
    # scene: small_warehouse_scene.py
```

**Example manifest.yaml for Preset environment:**
```yaml
id: indoor-environments-v1
type: preset
version: 1.0.0
description: Indoor navigation environments including hospital corridors and warehouse
category: navigation

preset_scenes:
  - scene_id: hospital
    description: Hospital corridor environment for indoor navigation
    preset: hospital_preset.py
  - scene_id: warehouse
    description: Warehouse with shelves and bounding walls
    preset: warehouse_preset.py
```

---

## Cache Management

### List Cached Environments

```bash
# List all cached environments
nepher cache list
```

### Clear Cache

```bash
# Clear cache for specific environment
nepher cache clear indoor-environments-v1

# Clear all cache
nepher cache clear
```

### Cache Information

```bash
# Show cache statistics
nepher cache info
```

Output example:
```
Cache Information:
  Cache Directory: /home/user/.nepher/cache
  Total Size: 1250.50 MB
  Environment Count: 5

  Environments:
    indoor-environments-v1: 450.25 MB
    outdoor-environments-v1: 320.10 MB
    ...
```

### Migrate Cache

```bash
# Move cache to new location
nepher cache migrate /new/cache/path
```

---

## Viewing Environments

### View Environment Information

```bash
# View environment details (required: --category)
nepher view indoor-environments-v1 --category navigation
nepher view digital-twin-warehouse-v1 --category navigation
nepher view outdoor-environments-v1 --category navigation

# View specific scene
nepher view indoor-environments-v1 --category navigation --scene hospital
nepher view indoor-environments-v1 --category navigation --scene warehouse
nepher view outdoor-environments-v1 --category navigation --scene park
nepher view outdoor-environments-v1 --category navigation --scene urban_street
nepher view digital-twin-warehouse-v1 --category navigation --scene small_warehouse
```

**Note:** Full Isaac Sim integration is planned for future releases.

---

## Python API

### Basic Usage

```python
import nepher

# Authentication
nepher.login("envhub_your_api_key")

# Configuration
nepher.config.set("cache_dir", "/custom/cache/path")
cache_dir = nepher.config.get("cache_dir")

# Load environments
env = nepher.load_env("indoor-environments-v1", category="navigation")
scene = nepher.load_scene(env, scene="hospital", category="navigation")

# Load USD environment
env = nepher.load_env("digital-twin-warehouse-v1", category="navigation")
scene = nepher.load_scene(env, scene="small_warehouse", category="navigation")

# List environments
envs = nepher.list_environments(category="navigation", benchmark=True)

# Download (with optional cache_dir override)
nepher.download("indoor-environments-v1", category="navigation", cache_dir="/tmp/cache")
nepher.download("waypoint-benchmark-v1", category="navigation")

# Upload
nepher.upload("./my-env", category="manipulation", benchmark=False)
```

### Advanced Usage

```python
from nepher import get_client, load_env, load_scene
from nepher.env_cfgs.navigation import UsdNavigationEnvCfg

# Get API client
client = get_client()

# List with filters
envs = client.list_environments(
    category="navigation",
    type="usd",
    benchmark=False,
    search="warehouse",
    limit=10
)

# Download environment
client.download_environment("indoor-environments-v1", dest_path="/tmp/bundle.zip")
client.download_environment("digital-twin-warehouse-v1", dest_path="/tmp/warehouse.zip")

# Upload environment
result = client.upload_environment(
    bundle_path="./my-env.zip",
    category="navigation",
    benchmark=False,
    duplicate_policy="reject"
)

# Load and use environment config
env = load_env("indoor-environments-v1", category="navigation")
scene_cfg = load_scene(env, scene="hospital", category="navigation")

# Load USD environment
env = load_env("digital-twin-warehouse-v1", category="navigation")
scene_cfg = load_scene(env, scene="small_warehouse", category="navigation")

# Use config in Isaac Lab
from isaaclab.envs import ManagerBasedRLEnv
# ... use scene_cfg to configure your environment
```

---

## Workflow Examples

### Example 1: Navigation Researcher

```bash
# 1. Authenticate
nepher login envhub_your_api_key

# 2. List available navigation environments
nepher list --category navigation

# 3. Download a benchmark environment
nepher download waypoint-benchmark-v1 --category navigation

# 4. Download indoor environments for testing
nepher download indoor-environments-v1 --category navigation

# 5. View available scenes
nepher view indoor-environments-v1 --category navigation

# 6. Use in your training script
python train.py --env waypoint-benchmark-v1 --scene basic_ground_waypoint
```

### Example 2: Working with USD Environments

```bash
# 1. Authenticate
nepher login envhub_your_api_key

# 2. List USD environments
nepher list --category navigation --type usd

# 3. Download USD warehouse environment
nepher download digital-twin-warehouse-v1 --category navigation

# 4. View environment details
nepher view digital-twin-warehouse-v1 --category navigation --scene small_warehouse

# 5. Use in your training script
python train.py --env digital-twin-warehouse-v1 --scene small_warehouse
```

### Example 3: Environment Contributor

```bash
# 1. Authenticate
nepher login envhub_your_api_key

# 2. Prepare your environment bundle
cd my-navigation-env
# ... create manifest.yaml, USD files or preset files, etc.

# 3. Upload preset navigation environment
nepher upload ./my-preset-env --category navigation

# 4. Upload USD navigation environment
nepher upload ./my-usd-env --category navigation

# 5. Upload as benchmark environment
nepher upload ./my-benchmark-env --category navigation --benchmark
```

### Example 4: Working with Multiple Environment Types

```bash
# 1. List all environments
nepher list

# 2. Download preset environments
nepher download indoor-environments-v1 --category navigation
nepher download outdoor-environments-v1 --category navigation

# 3. Download USD environments
nepher download digital-twin-warehouse-v1 --category navigation
nepher download usd-small-warehouse --category navigation

# 4. Check cache
nepher cache list
nepher cache info
```

### Example 5: Custom Cache Configuration

```bash
# 1. Set custom cache directory
nepher config set cache_dir /data/environments

# 2. Set category-specific cache
nepher config set categories.navigation.cache_dir /data/navigation-envs
nepher config set categories.manipulation.cache_dir /data/manipulation-envs

# 3. Download to custom locations
nepher download env1 --category navigation  # Uses /data/navigation-envs
nepher download env2 --category manipulation  # Uses /data/manipulation-envs

# 4. Migrate cache if needed
nepher cache migrate /new/cache/location
```

### Example 6: Python Script Workflow

```python
import nepher
from nepher import load_env, load_scene

# Configure
nepher.config.set("cache_dir", "/custom/cache")
nepher.login("envhub_api_key")

# Load preset environment
env = load_env("indoor-environments-v1", category="navigation")
print(f"Environment: {env.name}")
print(f"Scenes: {[s.name for s in env.get_all_scenes()]}")

# Load specific preset scene
scene_cfg = load_scene(env, scene="hospital", category="navigation")

# Load USD environment
env_usd = load_env("digital-twin-warehouse-v1", category="navigation")
scene_cfg_usd = load_scene(env_usd, scene="small_warehouse", category="navigation")

# Use in Isaac Lab
from isaaclab.envs import ManagerBasedRLEnv
# Configure your environment with scene_cfg
# ...
```

---

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

```bash
# Check if you're logged in
nepher whoami

# If not authenticated, login again
nepher login envhub_your_api_key
```

#### 2. Cache Directory Issues

```bash
# Check current cache directory
nepher config get cache_dir

# Set a writable cache directory
nepher config set cache_dir /path/to/writable/directory

# Check cache permissions
nepher cache info
```

#### 3. Download Failures

```bash
# Check network connection
nepher list  # Should work if API is accessible

# Try force re-download
nepher download <env_id> --category <category> --force

# Check cache space
nepher cache info
```

#### 4. Upload Failures

```bash
# Validate bundle structure
# Ensure manifest.yaml exists
ls my-environment/manifest.yaml

# Check bundle format
# Should be a directory with manifest.yaml
```

#### 5. Configuration Issues

```bash
# View current configuration
nepher config list

# Reset to defaults
nepher config reset

# Set via environment variables
export NEPHER_API_KEY="envhub_..."
export NEPHER_CACHE_DIR="/custom/path"
```

### Getting Help

```bash
# General help
nepher --help

# Command-specific help
nepher list --help
nepher download --help
nepher upload --help
nepher cache --help
nepher config --help
```

### Debug Mode

Set environment variable for verbose output:

```bash
export NEPHER_DEBUG=1
nepher list --category navigation
```

---

## Command Reference Summary

### Authentication
- `nepher login <api_key>` - Authenticate with API key
- `nepher logout` - Clear credentials
- `nepher whoami` - Show current user info

### Environment Management
- `nepher list [OPTIONS]` - List environments
- `nepher download <env_id> --category <category> [OPTIONS]` - Download environment
- `nepher upload <path> --category <category> [OPTIONS]` - Upload environment

### Cache Management
- `nepher cache list` - List cached environments
- `nepher cache clear [env_id]` - Clear cache
- `nepher cache info` - Show cache statistics
- `nepher cache migrate <new_path>` - Migrate cache

### Configuration
- `nepher config get <key>` - Get config value
- `nepher config set <key> <value>` - Set config value
- `nepher config list` - List all config
- `nepher config reset` - Reset to defaults

### Viewing
- `nepher view <env_id> --category <category> [--scene <scene>]` - View environment

---

## Additional Resources

- **Project Documentation**: See `NEPHER_PROJECT_DESCRIPTION.md` for architecture and design details
- **API Documentation**: See `envhub-backend` documentation for API endpoint details
- **Examples**: Check `environments/` directory for example environment bundles:
  - `digital-twin-warehouse-v1/` - USD warehouse environment
  - `indoor-environments-v1/` - Preset indoor scenes (hospital, warehouse)
  - `outdoor-environments-v1/` - Preset outdoor scenes (park, urban_street)
  - `usd-small-warehouse/` - USD small warehouse environment
  - `waypoint-benchmark-v1/` - Benchmark waypoint environment
  - `waypoint-sample-v1/` - Sample waypoint environment

---

## Quick Reference Card

```bash
# Setup
nepher login <api_key>
nepher config set cache_dir /path/to/cache

# Browse
nepher list --category navigation
nepher list --benchmark
nepher list --type usd
nepher list --type preset

# Download
nepher download indoor-environments-v1 --category navigation
nepher download digital-twin-warehouse-v1 --category navigation
nepher download waypoint-benchmark-v1 --category navigation

# Upload
nepher upload ./my-env --category navigation

# Manage
nepher cache list
nepher cache info
nepher cache clear <env_id>

# Configure
nepher config list
nepher config set <key> <value>
```

---

**Last Updated**: 2025
**Version**: 1.0.0

