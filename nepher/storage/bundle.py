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
        # Create destination directory
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)

        # Find and parse manifest
        manifest_path = dest_dir / "manifest.yaml"
        if not manifest_path.exists():
            raise ValueError(f"Manifest not found in bundle: {manifest_path}")

        # Parse manifest
        env = ManifestParser.parse(manifest_path)

        # Update paths to be relative to cache directory
        for scene in env.scenes:
            if scene.usd:
                scene.usd = dest_dir / scene.usd
            if scene.omap_meta:
                scene.omap_meta = dest_dir / scene.omap_meta

        env.cache_path = dest_dir

        return env

    @staticmethod
    def validate_bundle(zip_path: Path) -> bool:
        """
        Validate bundle structure.

        Args:
            zip_path: Path to bundle ZIP file

        Returns:
            True if valid, False otherwise
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                namelist = zip_ref.namelist()
                return "manifest.yaml" in namelist
        except Exception:
            return False

