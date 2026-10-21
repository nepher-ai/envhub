"""
Cache management for downloaded environments.

Handles user-configurable cache directories and cache operations.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from nepher.config import get_config
from nepher.storage.paths import safe_env_id


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


class CacheManager:
    """Manages local cache for environments."""

    def __init__(self, cache_dir: Optional[Path] = None, category: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Override cache directory (from CLI flag)
            category: Category for category-specific cache
        """
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir).expanduser().resolve()
        else:
            self.cache_dir = get_config().get_cache_dir(category=category)
        self.category = category

    def get_env_cache_path(self, env_id: str) -> Path:
        """Get cache path for a specific environment."""
        return self.cache_dir / safe_env_id(env_id)

    def is_cached(self, env_id: str) -> bool:
        """Check if environment is cached."""
        return (self.get_env_cache_path(env_id) / "manifest.yaml").is_file()

    def list_cached(self) -> List[str]:
        """List all cached environment IDs."""
        if not self.cache_dir.exists():
            return []

        try:
            return sorted(
                item.name
                for item in self.cache_dir.iterdir()
                if not item.name.startswith(".")
                and item.is_dir()
                and (item / "manifest.yaml").is_file()
            )
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Cannot access cache directory {self.cache_dir}: {e}") from e

    def clear_cache(self, env_id: Optional[str] = None) -> bool:
        """
        Clear cache.

        Args:
            env_id: Specific environment ID to clear, or None to clear all cached environments

        Returns:
            True if anything was removed.

        Raises:
            RuntimeError: If cache directory cannot be accessed
        """
        try:
            if env_id:
                cache_path = self.get_env_cache_path(env_id)
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                    return True
                return False

            removed = False
            for cached_id in self.list_cached():
                shutil.rmtree(self.cache_dir / cached_id)
                removed = True
            return removed
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Cannot clear cache: {e}") from e

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics."""
        environments = []
        for env_id in self.list_cached():
            try:
                size = _dir_size(self.cache_dir / env_id)
            except (PermissionError, OSError):
                continue
            environments.append({"id": env_id, "size": size})

        return {
            "cache_dir": str(self.cache_dir),
            "total_size": sum(e["size"] for e in environments),
            "env_count": len(environments),
            "environments": environments,
        }

    def migrate_cache(self, new_cache_dir: Path, update_config: bool = True):
        """
        Move cached environments to a new location.

        Args:
            new_cache_dir: New cache directory path
            update_config: Persist the new location as ``cache_dir`` so later
                commands (and npcli) use it.

        Raises:
            RuntimeError: If migration fails
        """
        new_cache_dir = Path(new_cache_dir).expanduser().resolve()
        if new_cache_dir == self.cache_dir:
            return

        try:
            new_cache_dir.mkdir(parents=True, exist_ok=True)
            for env_id in self.list_cached():
                new_path = new_cache_dir / env_id
                if new_path.exists():
                    raise RuntimeError(f"{new_path} already exists")
                shutil.move(str(self.cache_dir / env_id), str(new_path))
        except (PermissionError, OSError, shutil.Error) as e:
            raise RuntimeError(f"Cannot migrate cache to {new_cache_dir}: {e}") from e

        self.cache_dir = new_cache_dir
        if update_config:
            key = f"categories.{self.category}.cache_dir" if self.category else "cache_dir"
            get_config().set(key, str(new_cache_dir), save=True)


def get_cache_manager(
    cache_dir: Optional[Path] = None, category: Optional[str] = None
) -> CacheManager:
    """Return a cache manager for the given override / category."""
    return CacheManager(cache_dir=cache_dir, category=category)
