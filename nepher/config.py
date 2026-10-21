"""
Configuration management for Nepher.

Supports multiple configuration sources with priority:
1. CLI arguments
2. Environment variables
3. Config file
4. Category-specific overrides
5. Default values

The API URL and cache settings follow the same rules as ``npcli envhub`` so both
CLIs talk to the same backend and share one cache.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11


DEFAULT_API_URL = "https://api.nepher.ai/envhub"

# Older releases wrote every default (including this URL) into config.toml, so
# a persisted legacy value means "unset", not an explicit user choice.
LEGACY_API_URLS = frozenset({"https://envhub-api.nepher.ai", "https://envhub-api.nepher.ai/"})

DEFAULTS: Dict[str, Any] = {
    "api_url": DEFAULT_API_URL,
    "cache_dir": "~/.nepher/cache",
    "default_category": None,
    "categories": {},
}


def _env_api_url() -> Optional[str]:
    """API URL from the environment, using the same precedence as npcli."""
    for var in ("NEPHER_ENVHUB_API_URL", "ENVHUB_API_URL"):
        value = os.getenv(var)
        if value:
            return value
    website = os.getenv("NEPHER_API_URL")
    if website:
        return f"{website.rstrip('/')}/envhub"
    return None


def _load_file(path: Path) -> Dict[str, Any]:
    """Parse a config file; ``.nepherrc`` may be TOML or JSON."""
    raw = path.read_bytes()
    if path.suffix == ".json":
        data = json.loads(raw.decode("utf-8"))
    elif path.suffix == ".toml":
        data = tomllib.loads(raw.decode("utf-8"))
    else:
        text = raw.decode("utf-8")
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            data = json.loads(text)
    return data if isinstance(data, dict) else {}


class Config:
    """Centralized configuration manager."""

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._file_config: Dict[str, Any] = {}
        self._config_file: Optional[Path] = None
        self._load_config()

    def _load_config(self):
        """Load configuration from all sources."""
        self._file_config = {}
        self._config_file = self._find_config_file()
        if self._config_file is not None:
            try:
                self._file_config = _load_file(self._config_file)
            except (OSError, ValueError, tomllib.TOMLDecodeError):
                self._file_config = {}

        if self._file_config.get("api_url") in LEGACY_API_URLS:
            self._file_config.pop("api_url")
        # API keys are kept in credential storage, never in the config file.
        self._file_config.pop("api_key", None)

        self._config = {**DEFAULTS, "categories": {}}
        self._config.update(self._file_config)

        env_url = _env_api_url()
        if env_url:
            self._config["api_url"] = env_url
        if os.getenv("NEPHER_CACHE_DIR"):
            self._config["cache_dir"] = os.getenv("NEPHER_CACHE_DIR")

    def _find_config_file(self) -> Optional[Path]:
        """Find config file in standard locations."""
        cwd_config = Path.cwd() / ".nepherrc"
        if cwd_config.is_file():
            return cwd_config

        home_dir = Path.home() / ".nepher"
        for name in ("config.toml", "config.json"):
            candidate = home_dir / name
            if candidate.is_file():
                return candidate

        return None

    def reload(self):
        """Re-read configuration from disk and the environment."""
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Supports dot notation for nested keys (e.g., 'categories.navigation.cache_dir').
        """
        value: Any = self._config
        for k in key.split("."):
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any, save: bool = True):
        """
        Set configuration value.

        Supports dot notation for nested keys. Only explicitly set values are
        written to disk, so defaults can change in future releases.
        """
        if key == "api_key":
            raise ValueError("Use 'nepher login' to store an API key; it is not kept in config.")

        keys = key.split(".")
        for target in (self._config, self._file_config):
            node = target
            for k in keys[:-1]:
                if k not in node or not isinstance(node[k], dict):
                    node[k] = {}
                node = node[k]
            node[keys[-1]] = value

        if save:
            self._save_config()

    def reset(self) -> bool:
        """Delete the config file and restore defaults. Returns True if a file was removed."""
        removed = False
        if self._config_file is not None and self._config_file.exists():
            self._config_file.unlink()
            removed = True
        self._config_file = None
        self._load_config()
        return removed

    def get_cache_dir(self, category: Optional[str] = None, override: Optional[str] = None) -> Path:
        """
        Get cache directory path (not created).

        Priority:
        1. override (CLI argument)
        2. Category-specific cache_dir
        3. Global cache_dir
        4. Default
        """
        if override:
            path_str = override
        elif category:
            cat_config = self.get(f"categories.{category}", {}) or {}
            path_str = cat_config.get("cache_dir") or self.get("cache_dir")
        else:
            path_str = self.get("cache_dir")

        return Path(path_str).expanduser().resolve()

    def get_api_url(self) -> str:
        """Get API URL."""
        return str(self.get("api_url")).rstrip("/")

    def get_api_key(self) -> Optional[str]:
        """Get the API key from credential storage (env var, nepher login, or npcli login)."""
        from nepher.credentials import resolve_api_key

        return resolve_api_key()

    def _remove_none_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively remove None values from dictionary for TOML serialization."""
        result = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, dict):
                cleaned = self._remove_none_values(value)
                if cleaned:
                    result[key] = cleaned
            else:
                result[key] = value
        return result

    def _save_config(self):
        """Save explicitly set configuration values to file."""
        if self._config_file is None:
            config_dir = Path.home() / ".nepher"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_file = config_dir / "config.toml"

        data = self._remove_none_values(self._file_config)
        if self._config_file.suffix == ".json" or self._config_file.name == ".nepherrc":
            self._config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return

        try:
            import tomli_w
        except ImportError:
            self._config_file = self._config_file.with_suffix(".json")
            self._config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return

        with open(self._config_file, "wb") as f:
            tomli_w.dump(data, f)


_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def set_config(key: str, value: Any, save: bool = True):
    """Set configuration value."""
    get_config().set(key, value, save=save)
