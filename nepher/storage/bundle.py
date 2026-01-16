"""
Bundle validation and extraction.
"""

import zipfile
import shutil
from pathlib import Path
from typing import Optional
from nepher.storage.manifest import ManifestParser
from nepher.core import Environment


class BundleManager:
    """Manages environment bundle operations."""

    @staticmethod
    def extract_bundle(zip_path: Path, dest_dir: Path) -> Environment:
        """
        Extract and validate bundle.

        Args:
            zip_path: Path to bundle ZIP file
            dest_dir: Destination directory for extraction

        Returns:
            Environment object from manifest
        """
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(dest_dir)
        except zipfile.BadZipFile as e:
            raise ValueError(f"Invalid ZIP file: {zip_path}") from e
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Cannot extract bundle to {dest_dir}: {e}") from e

        manifest_path = dest_dir / "manifest.yaml"
        if not manifest_path.exists():
            raise ValueError(f"Manifest not found in bundle: {manifest_path}")

        env = ManifestParser.parse(manifest_path)

        for scene in env.scenes:
            if scene.usd:
                scene.usd = dest_dir / scene.usd
            if scene.omap_meta:
                scene.omap_meta = dest_dir / scene.omap_meta

        env.cache_path = dest_dir

        return env

    @staticmethod
    def validate_bundle(bundle_path: Path) -> bool:
        """
        Validate bundle structure.

        Args:
            bundle_path: Path to bundle (ZIP file or directory)

        Returns:
            True if valid, False otherwise
        """
        try:
            if bundle_path.is_dir():
                manifest_path = bundle_path / "manifest.yaml"
                return manifest_path.exists()
            
            if bundle_path.suffix.lower() == ".zip":
                with zipfile.ZipFile(bundle_path, "r") as zip_ref:
                    namelist = zip_ref.namelist()
                    return "manifest.yaml" in namelist
            
            return False
        except Exception:
            return False

