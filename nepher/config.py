"""
Configuration management for Nepher.

Supports multiple configuration sources with priority:
1. CLI arguments
2. Environment variables
3. Config file
4. Category-specific overrides
5. Default values
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11


class Config:
    """Centralized configuration manager."""

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._config_file: Optional[Path] = None
        self._load_config()

    def _load_config(self):
        """Load configuration from all sources."""
        self._config = {
            "api_url": "http://localhost:8000",
            "api_key": None,
            "cache_dir": "~/.nepher/cache",
            "default_category": None,
            "categories": {},
        }

        config_file = self._find_config_file()
        if config_file and config_file.exists():
            self._config_file = config_file
            try:
                if config_file.suffix == ".toml":
                    with open(config_file, "rb") as f:
                        file_config = tomllib.load(f)
                        self._config.update(file_config)
                elif config_file.suffix == ".json":
                    import json

                    with open(config_file, "r") as f:
                        file_config = json.load(f)
                        self._config.update(file_config)
            except Exception:
                pass

        if os.getenv("NEPHER_API_URL"):
            self._config["api_url"] = os.getenv("NEPHER_API_URL")
        if os.getenv("NEPHER_API_KEY"):
            self._config["api_key"] = os.getenv("NEPHER_API_KEY")
        if os.getenv("NEPHER_CACHE_DIR"):
            self._config["cache_dir"] = os.getenv("NEPHER_CACHE_DIR")

    def _find_config_file(self) -> Optional[Path]:
        """Find config file in standard locations."""
        cwd_config = Path.cwd() / ".nepherrc"
        if cwd_config.exists():
            return cwd_config

        home_config = Path.home() / ".nepher" / "config.toml"
        if home_config.exists():
            return home_config

        return None

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Supports dot notation for nested keys (e.g., 'categories.navigation.cache_dir').
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any, save: bool = True):
        """
        Set configuration value.

        Supports dot notation for nested keys.
        Creates config file if it doesn't exist.
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

        if save:
            self._save_config()

    def get_cache_dir(self, category: Optional[str] = None, override: Optional[str] = None) -> Path:
        """
        Get cache directory path.

        Priority:
        1. override (CLI argument)
        2. Category-specific cache_dir
        3. Global cache_dir
        4. Default

        Args:
            category: Optional category name for category-specific cache
            override: Optional override path (from CLI flag)

        Returns:
            Resolved Path object
        """
        if override:
            path_str = override
        elif category:
            cat_config = self.get(f"categories.{category}", {})
            path_str = cat_config.get("cache_dir") or self.get("cache_dir")
        else:
            path_str = self.get("cache_dir")

        path = Path(path_str).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)

        return path

    def get_api_url(self) -> str:
        """Get API URL."""
        return self.get("api_url")

    def get_api_key(self) -> Optional[str]:
        """Get API key (may be None if not set)."""
        return self.get("api_key")

    def _remove_none_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively remove None values from dictionary for TOML serialization."""
        result = {}
        for key, value in data.items():
            if value is None:
                continue  # Skip None values
            elif isinstance(value, dict):
                cleaned = self._remove_none_values(value)
                if cleaned:  # Only include non-empty dicts
                    result[key] = cleaned
            else:
                result[key] = value
        return result

    def _save_config(self):
        """Save configuration to file."""
        if not self._config_file:
            config_dir = Path.home() / ".nepher"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_file = config_dir / "config.toml"

        try:
            import tomli_w

            config_to_save = self._remove_none_values(self._config)

            with open(self._config_file, "wb") as f:
                tomli_w.dump(config_to_save, f)
        except ImportError:
            import json

            with open(self._config_file.with_suffix(".json"), "w") as f:
                json.dump(self._config, f, indent=2)


_config_instance: Optional[Config] = None


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def set_config(key: str, value: Any, save: bool = True):
    """Set configuration value."""
    get_config().set(key, value, save=save)

