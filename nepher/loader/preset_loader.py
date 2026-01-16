"""
Preset environment loader.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional
from nepher.core import Environment
from nepher.loader.base import BaseLoader
from nepher.env_cfgs.registry import get_config_class


def load_preset_module(preset_path: str, base_path: Optional[Path] = None):
    """Load preset module from path.
    
    Args:
        preset_path: Path to preset file (e.g., "my_preset.py") or module path
        base_path: Base directory for resolving relative file paths
    
    Returns:
        Preset config class
        
    Raises:
        FileNotFoundError: If preset file is not found
        ImportError: If preset module cannot be loaded
        ValueError: If no preset config class is found
    """
    if preset_path.endswith(".py"):
        if base_path:
            file_path = base_path / preset_path
        else:
            file_path = Path(preset_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Preset file not found: {file_path}")
        
        module_name = f"nepher_preset_{file_path.stem}_{id(file_path)}"
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load preset from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                (attr_name.endswith("Cfg") or attr_name.endswith("PresetCfg")) and
                attr_name != "PresetNavigationEnvCfg"):
                return attr
        
        raise ValueError(f"No preset config class found in {file_path}")
    else:
        parts = preset_path.split(".")
        module_path = ".".join(parts[:-1])
        class_name = parts[-1]
        
        module = importlib.import_module(module_path)
        return getattr(module, class_name)


class PresetLoader(BaseLoader):
    """Generic preset loader that returns category-specific configs."""

    def load(self, env: Environment, scene_idx: int, category: str):
        """Load preset scene config."""
        if scene_idx >= len(env.preset_scenes):
            raise IndexError(f"Preset scene index {scene_idx} out of range")

        scene = env.preset_scenes[scene_idx]

        if not scene.preset:
            raise ValueError("Preset scene missing preset path")

        preset_class = load_preset_module(scene.preset, base_path=env.cache_path)
        return preset_class()

