"""
Loader registry and convenience functions.
"""

from typing import Optional
from nepher.core import Environment
from nepher.storage.cache import get_cache_manager
from nepher.storage.manifest import ManifestParser
from nepher.api.client import get_client
from nepher.loader.usd_loader import UsdLoader
from nepher.loader.preset_loader import PresetLoader


def load_env(env_id: str, category: str) -> Environment:
    """
    Load environment from cache or download if needed.

    Args:
        env_id: Environment ID
        category: Environment category

    Returns:
        Environment object
    """
    cache_manager = get_cache_manager(category=category)
    cache_path = cache_manager.get_env_cache_path(env_id)

    # Check if cached
    if cache_manager.is_cached(env_id):
        manifest_path = cache_path / "manifest.yaml"
        return ManifestParser.parse(manifest_path)

    # Not cached - would need to download
    # For now, raise error - download should be done separately
    raise FileNotFoundError(
        f"Environment {env_id} not found in cache. Use download() first."
    )


def load_scene(env: Environment, scene: str | int, category: str):
    """
    Load scene config.

    Args:
        env: Environment object
        scene: Scene name or index
        category: Environment category

    Returns:
        Category-appropriate config class
    """
    # Find scene
    scene_obj = env.get_scene(scene)
    if not scene_obj:
        raise ValueError(f"Scene {scene} not found in environment {env.id}")

    # Determine loader type
    if scene_obj.usd:
        loader = UsdLoader()
        scene_idx = env.scenes.index(scene_obj)
        return loader.load(env, scene_idx, category)
    elif scene_obj.preset:
        loader = PresetLoader()
        scene_idx = env.preset_scenes.index(scene_obj)
        return loader.load(env, scene_idx, category)
    else:
        raise ValueError(f"Scene {scene} has no USD or preset path")

