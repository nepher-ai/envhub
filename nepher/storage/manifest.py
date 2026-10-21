"""
Manifest parsing for environment bundles.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from nepher.core import Environment, Scene
from nepher.storage.paths import resolve_within


class ManifestParser:
    """Parser for environment manifest files."""

    @staticmethod
    def parse(manifest_path: Path) -> Environment:
        """
        Parse manifest YAML file.

        Asset paths (``usd``, ``omap_meta``) are resolved to absolute paths
        inside the bundle directory; paths that point outside it are rejected.

        Args:
            manifest_path: Path to manifest.yaml

        Returns:
            Environment object
        """
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in manifest file {manifest_path}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Manifest must be a YAML mapping: {manifest_path}")

        bundle_dir = manifest_path.parent.resolve()

        def asset(entry: Dict[str, Any], key: str) -> Optional[Path]:
            value = entry.get(key)
            return resolve_within(bundle_dir, value) if value else None

        env_id = str(data.get("id") or manifest_path.parent.name)

        scenes = []
        for scene_data in data.get("scenes") or []:
            scenes.append(
                Scene(
                    name=scene_data.get("scene_id") or scene_data.get("name", ""),
                    description=scene_data.get("description"),
                    usd=asset(scene_data, "usd"),
                    scene=scene_data.get("scene"),
                    omap_meta=asset(scene_data, "omap_meta"),
                    metadata=scene_data.get("metadata"),
                )
            )

        preset_scenes = []
        for preset_data in data.get("preset_scenes") or []:
            preset_scenes.append(
                Scene(
                    name=preset_data.get("scene_id") or preset_data.get("name", ""),
                    description=preset_data.get("description"),
                    preset=preset_data.get("preset"),
                    metadata=preset_data.get("metadata"),
                )
            )

        return Environment(
            id=env_id,
            name=data.get("name", env_id),
            description=data.get("description"),
            category=data.get("category", "navigation"),
            type="preset" if preset_scenes else "usd",
            version=data.get("version"),
            author=data.get("author"),
            scenes=scenes,
            preset_scenes=preset_scenes,
            benchmark=bool(data.get("benchmark", False)),
            metadata=data.get("metadata") or {},
            cache_path=bundle_dir,
        )
