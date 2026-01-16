"""
USD environment loader.
"""

from pathlib import Path
from nepher.core import Environment
from nepher.loader.base import BaseLoader
from nepher.loader.preset_loader import load_preset_module
from nepher.env_cfgs.registry import get_config_class


class UsdLoader(BaseLoader):
    """Generic USD loader that returns category-specific configs."""

    def load(self, env: Environment, scene_idx: int, category: str):
        """Load USD scene config.
        
        If the scene has a Python scene file, it will be loaded and used to configure
        the USD environment. Otherwise, a basic config is created from the manifest.
        """
        if scene_idx >= len(env.scenes):
            raise IndexError(f"Scene index {scene_idx} out of range")

        scene = env.scenes[scene_idx]

        if scene.scene:
            scene_class = load_preset_module(scene.scene, base_path=env.cache_path)
            cfg = scene_class()
            
            if scene.usd and not cfg.usd_path:
                cfg.usd_path = str(scene.usd)
            if scene.omap_meta and not cfg.occupancy_map_yaml:
                cfg.occupancy_map_yaml = str(scene.omap_meta)
            if scene.name and not cfg.name:
                cfg.name = scene.name
            if scene.description and not cfg.description:
                cfg.description = scene.description
            
            return cfg
        
        config_class = get_config_class(category=category, type="usd")
        cfg = config_class()
        cfg.usd_path = str(scene.usd) if scene.usd else None
        cfg.occupancy_map_yaml = str(scene.omap_meta) if scene.omap_meta else None
        cfg.name = scene.name
        cfg.description = scene.description

        return cfg

