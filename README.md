# Nepher: Universal Isaac Lab Environments Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Nepher** is a unified, category-agnostic Python package for managing Isaac Lab environments across all categories (navigation, manipulation, humanoid, locomotion, etc.). It provides a professional command-line interface and Python API for discovering, downloading, uploading, and managing environment bundles for Isaac Lab/Isaac Sim.

## Installation

```bash
pip install nepher
```

## Quick Start

```bash
# Authenticate with your API key
nepher login <api_key>

# List available environments
nepher list --category navigation

# Download an environment
nepher download <env_id> --category navigation

# Upload your own environment
nepher upload ./my-env --category manipulation
```

## Features

- **Universal Category Support**: Works with any environment category (navigation, manipulation, humanoid, locomotion, etc.)
- **Professional CLI**: Intuitive commands inspired by tools like `wandb`
- **Seamless Integration**: Direct integration with `envhub-backend` API
- **Flexible Configuration**: User-configurable cache directories and settings
- **Backward Compatible**: Maintains compatibility with existing `envs-nav` workflows

## Documentation

See [NEPHER_PROJECT_DESCRIPTION.md](../NEPHER_PROJECT_DESCRIPTION.md) for complete project documentation.

## License

MIT License - see [LICENSE](LICENSE) for details.

