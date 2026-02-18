"""
Loader registry and convenience functions.
"""

from typing import Optional, Union
from nepher.core import Environment
from nepher.storage.cache import get_cache_manager
from nepher.storage.manifest import ManifestParser
from nepher.api.client import get_client
from nepher.loader.usd_loader import UsdLoader
from nepher.loader.preset_loader import PresetLoader


def load_env(env_id: str, category: Optional[str] = None) -> Environment:
    """
    Load environment from cache or download if needed.

    Args:
        env_id: Environment ID
        category: Environment category (optional, used for cache dir resolution)

    Returns:
        Environment object
    """
    cache_manager = get_cache_manager(category=category)
    cache_path = cache_manager.get_env_cache_path(env_id)

    if cache_manager.is_cached(env_id):
        manifest_path = cache_path / "manifest.yaml"
        return ManifestParser.parse(manifest_path)

    raise FileNotFoundError(
        f"Environment {env_id} not found in cache. Use 'nepher download {env_id}' first."
    )


def load_scene(env: Environment, scene: Union[str, int], category: Optional[str] = None):
    """
    Load scene config.

    Args:
        env: Environment object
        scene: Scene name or index
        category: Environment category (optional, falls back to env.category from manifest)

    Returns:
        Category-appropriate config class
    """
    resolved_category = category or env.category

    scene_obj = env.get_scene(scene)
    if not scene_obj:
        raise ValueError(f"Scene {scene} not found in environment {env.id}")

    if scene_obj.usd:
        loader = UsdLoader()
        scene_idx = env.scenes.index(scene_obj)
        return loader.load(env, scene_idx, resolved_category)
    elif scene_obj.preset:
        loader = PresetLoader()
        scene_idx = env.preset_scenes.index(scene_obj)
        return loader.load(env, scene_idx, resolved_category)
    else:
        raise ValueError(f"Scene {scene} has no USD or preset path")

