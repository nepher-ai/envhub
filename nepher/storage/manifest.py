"""
Manifest parsing for environment bundles.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from nepher.core import Environment, Scene


class ManifestParser:
    """Parser for environment manifest files."""

    @staticmethod
    def parse(manifest_path: Path) -> Environment:
        """
        Parse manifest YAML file.

        Args:
            manifest_path: Path to manifest.yaml

        Returns:
            Environment object
        """
        with open(manifest_path, "r") as f:
            data = yaml.safe_load(f)

        env_id = data.get("id", manifest_path.parent.name)
        name = data.get("name", env_id)
        description = data.get("description")
        category = data.get("category", "navigation")
        version = data.get("version")
        author = data.get("author")
        benchmark = data.get("benchmark", False)
        metadata = data.get("metadata", {})

        # Determine type
        env_type = "preset" if data.get("preset_scenes") else "usd"

        # Parse scenes
        scenes = []
        for scene_data in data.get("scenes", []):
            scene = Scene(
                name=scene_data.get("scene_id") or scene_data.get("name", ""),
                description=scene_data.get("description"),
                usd=Path(scene_data["usd"]) if scene_data.get("usd") else None,
                scene=scene_data.get("scene"),  # Python scene file for USD scenes
                omap_meta=Path(scene_data["omap_meta"]) if scene_data.get("omap_meta") else None,
                metadata=scene_data.get("metadata"),
            )
            scenes.append(scene)

        # Parse preset scenes
        preset_scenes = []
        for preset_data in data.get("preset_scenes", []):
            scene = Scene(
                name=preset_data.get("scene_id") or preset_data.get("name", ""),
                description=preset_data.get("description"),
                preset=preset_data.get("preset"),
                metadata=preset_data.get("metadata"),
            )
            preset_scenes.append(scene)

        return Environment(
            id=env_id,
            name=name,
            description=description,
            category=category,
            type=env_type,
            version=version,
            author=author,
            scenes=scenes,
            preset_scenes=preset_scenes,
            benchmark=benchmark,
            metadata=metadata,
            cache_path=manifest_path.parent,
        )

