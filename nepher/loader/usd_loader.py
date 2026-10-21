"""
USD environment loader.
"""

from pathlib import Path
from typing import Optional
from nepher.core import Environment
from nepher.loader.base import BaseLoader
from nepher.loader.preset_loader import load_preset_module
from nepher.env_cfgs.registry import get_config_class
from nepher.storage.paths import resolve_within


def _bundle_path(env: Environment, value: Optional[str]) -> Optional[str]:
    """Resolve a bundle-relative path from a scene file against the bundle directory."""
    if not value or env.cache_path is None or Path(value).is_absolute():
        return value
    return str(resolve_within(Path(env.cache_path), value))


class UsdLoader(BaseLoader):
    """Generic USD loader that returns category-specific configs."""

    def load(self, env: Environment, scene_idx: int, category: str):
        """Load USD scene config.

        If the scene has a Python scene file, it will be loaded and used to configure
        the USD environment. Otherwise, a basic config is created from the manifest.
        Relative ``usd_path`` / ``occupancy_map_yaml`` values are resolved against
        the bundle directory.
        """
        if scene_idx >= len(env.scenes):
            raise IndexError(f"Scene index {scene_idx} out of range")

        scene = env.scenes[scene_idx]

        if scene.scene:
            if not scene.scene.endswith(".py"):
                raise ValueError(f"Scene file must be a .py file inside the bundle: {scene.scene!r}")
            scene_class = load_preset_module(scene.scene, base_path=env.cache_path)
            cfg = scene_class()

            if scene.name and not cfg.name:
                cfg.name = scene.name
            if scene.description and not cfg.description:
                cfg.description = scene.description
            usd_path = cfg.usd_path or (str(scene.usd) if scene.usd else None)
            omap = getattr(cfg, "occupancy_map_yaml", None) or (
                str(scene.omap_meta) if scene.omap_meta else None
            )
        else:
            cfg = get_config_class(category=category, type="usd")()
            cfg.name = scene.name
            cfg.description = scene.description
            usd_path = str(scene.usd) if scene.usd else None
            omap = str(scene.omap_meta) if scene.omap_meta else None

        cfg.usd_path = _bundle_path(env, usd_path)

        if hasattr(cfg, "occupancy_map_yaml"):
            omap = _bundle_path(env, omap)
            if omap != cfg.occupancy_map_yaml:
                cfg.occupancy_map_yaml = omap
                # The position strategy is built in __post_init__ from these
                # fields, so rebuild it now that the map path is known.
                if hasattr(cfg, "position_strategy") and hasattr(cfg, "__post_init__"):
                    cfg.__post_init__()

        return cfg
