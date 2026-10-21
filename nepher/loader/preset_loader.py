"""
Preset environment loader.
"""

import hashlib
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Optional
from nepher.core import Environment
from nepher.loader.base import BaseLoader
from nepher.env_cfgs.base import BaseEnvCfg
from nepher.storage.paths import resolve_within


def load_preset_module(preset_path: str, base_path: Optional[Path] = None):
    """Load preset module from path.

    Preset files are executed as Python, so only load bundles you trust.
    When ``base_path`` is given (a bundle directory), the file must live inside it.

    Args:
        preset_path: Path to preset file (e.g., "my_preset.py") or module path
        base_path: Base directory for resolving relative file paths

    Returns:
        Preset config class

    Raises:
        FileNotFoundError: If preset file is not found
        ImportError: If preset module cannot be loaded
        ValueError: If no preset config class is found or the path escapes the bundle
    """
    if preset_path.endswith(".py"):
        if base_path:
            file_path = resolve_within(Path(base_path), preset_path)
        else:
            file_path = Path(preset_path).resolve()

        if not file_path.is_file():
            raise FileNotFoundError(f"Preset file not found: {file_path}")

        digest = hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()[:12]
        module_name = f"nepher_preset_{file_path.stem}_{digest}"
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load preset from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(module_name, None)
            raise

        # Only classes *defined in this file* (not imports like AssetBaseCfg or
        # PresetNavigationEnvCfg) and subclasses of BaseEnvCfg are env presets.
        candidates: list[type] = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, type):
                continue
            if not (attr_name.endswith("Cfg") or attr_name.endswith("PresetCfg")):
                continue
            if getattr(attr, "__module__", None) != module.__name__:
                continue
            try:
                if issubclass(attr, BaseEnvCfg) and attr is not BaseEnvCfg:
                    candidates.append(attr)
            except TypeError:
                continue

        if not candidates:
            raise ValueError(
                f"No preset config class found in {file_path}. "
                "Define a subclass of BaseEnvCfg in this file (imports like "
                "AssetBaseCfg are ignored)."
            )
        if len(candidates) > 1:
            # Prefer the most specific subclass (deepest in inheritance).
            candidates.sort(
                key=lambda c: len(c.__mro__),
                reverse=True,
            )
        return candidates[0]
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

