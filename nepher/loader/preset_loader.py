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
    """
    # Check if it's a file path (ends with .py) or module path
    if preset_path.endswith(".py"):
        # File path - load from file
        if base_path:
            file_path = base_path / preset_path
        else:
            file_path = Path(preset_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Preset file not found: {file_path}")
        
        # Generate a unique module name based on the file path
        # Use a name that won't conflict with existing modules
        module_name = f"nepher_preset_{file_path.stem}_{id(file_path)}"
        
        # Load module from file
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load preset from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        # Register module in sys.modules BEFORE executing it
        # This is required for @configclass to work properly
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Find the config class (usually ends with "Cfg" or "PresetCfg")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                (attr_name.endswith("Cfg") or attr_name.endswith("PresetCfg")) and
                attr_name != "PresetNavigationEnvCfg"):  # Exclude base class
                return attr
        
        raise ValueError(f"No preset config class found in {file_path}")
    else:
        # Module path - assume it's a module path like "my_package.my_module.MyPreset"
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

        # Load preset module
        preset_class = load_preset_module(scene.preset, base_path=env.cache_path)

        # Presets are category-specific by design, so we just return them
        return preset_class()

