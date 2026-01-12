"""
Core data structures for Nepher.

Defines Environment, Scene, and related types.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class Scene:
    """Represents a single scene within an environment."""

    name: str
    description: Optional[str] = None
    usd: Optional[Path] = None
    preset: Optional[str] = None
    scene: Optional[str] = None  # Python scene file path (for USD scenes with custom config)
    omap_meta: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Environment:
    """Represents an environment bundle."""

    id: str
    name: str
    description: Optional[str] = None
    category: str = "navigation"
    type: str = "usd"  # "usd" or "preset"
    version: Optional[str] = None
    author: Optional[str] = None
    scenes: List[Scene] = None
    preset_scenes: List[Scene] = None
    benchmark: bool = False
    metadata: Optional[Dict[str, Any]] = None
    cache_path: Optional[Path] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.scenes is None:
            self.scenes = []
        if self.preset_scenes is None:
            self.preset_scenes = []

    def get_scene(self, scene: str | int) -> Optional[Scene]:
        """
        Get a scene by name or index.

        Args:
            scene: Scene name (str) or index (int)

        Returns:
            Scene object or None if not found
        """
        all_scenes = self.scenes + self.preset_scenes

        if isinstance(scene, int):
            if 0 <= scene < len(all_scenes):
                return all_scenes[scene]
        else:
            for s in all_scenes:
                if s.name == scene:
                    return s

        return None

    def get_all_scenes(self) -> List[Scene]:
        """Get all scenes (USD and preset combined)."""
        return self.scenes + self.preset_scenes

