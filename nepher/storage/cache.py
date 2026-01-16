"""
Cache management for downloaded environments.

Handles user-configurable cache directories and cache operations.
"""

import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from nepher.config import get_config


class CacheManager:
    """Manages local cache for environments."""

    def __init__(self, cache_dir: Optional[Path] = None, category: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Override cache directory (from CLI flag)
            category: Category for category-specific cache
        """
        config = get_config()
        self.cache_dir = cache_dir or config.get_cache_dir(category=category)
        self.category = category

    def get_env_cache_path(self, env_id: str) -> Path:
        """Get cache path for a specific environment."""
        return self.cache_dir / env_id

    def is_cached(self, env_id: str) -> bool:
        """Check if environment is cached."""
        cache_path = self.get_env_cache_path(env_id)
        return cache_path.exists() and (cache_path / "manifest.yaml").exists()

    def list_cached(self) -> List[str]:
        """
        List all cached environment IDs.
        
        Returns:
            List of cached environment ID strings
        """
        if not self.cache_dir.exists():
            return []

        cached = []
        try:
            for item in self.cache_dir.iterdir():
                if item.is_dir() and (item / "manifest.yaml").exists():
                    cached.append(item.name)
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Cannot access cache directory {self.cache_dir}: {e}") from e

        return cached

    def clear_cache(self, env_id: Optional[str] = None):
        """
        Clear cache.

        Args:
            env_id: Specific environment ID to clear, or None to clear all
            
        Raises:
            RuntimeError: If cache directory cannot be accessed
        """
        try:
            if env_id:
                cache_path = self.get_env_cache_path(env_id)
                if cache_path.exists():
                    shutil.rmtree(cache_path)
            else:
                if self.cache_dir.exists():
                    shutil.rmtree(self.cache_dir)
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Cannot clear cache: {e}") from e

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.cache_dir.exists():
            return {
                "cache_dir": str(self.cache_dir),
                "total_size": 0,
                "env_count": 0,
                "environments": [],
            }

        envs = self.list_cached()
        total_size = 0
        env_sizes = {}

        for env_id in envs:
            try:
                env_path = self.get_env_cache_path(env_id)
                size = sum(f.stat().st_size for f in env_path.rglob("*") if f.is_file())
                env_sizes[env_id] = size
                total_size += size
            except (PermissionError, OSError):
                continue

        return {
            "cache_dir": str(self.cache_dir),
            "total_size": total_size,
            "env_count": len(envs),
            "environments": [{"id": eid, "size": env_sizes[eid]} for eid in envs],
        }

    def migrate_cache(self, new_cache_dir: Path):
        """
        Migrate cache to new location.

        Args:
            new_cache_dir: New cache directory path
            
        Raises:
            RuntimeError: If migration fails
        """
        if not self.cache_dir.exists():
            return

        try:
            new_cache_dir.mkdir(parents=True, exist_ok=True)

            for env_id in self.list_cached():
                old_path = self.get_env_cache_path(env_id)
                new_path = new_cache_dir / env_id
                shutil.move(str(old_path), str(new_path))
        except (PermissionError, OSError, shutil.Error) as e:
            raise RuntimeError(f"Cannot migrate cache to {new_cache_dir}: {e}") from e


# Global cache manager instance
_cache_manager_instance: Optional[CacheManager] = None


def get_cache_manager(
    cache_dir: Optional[Path] = None, category: Optional[str] = None
) -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager(cache_dir=cache_dir, category=category)
    return _cache_manager_instance

