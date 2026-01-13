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
    def validate_bundle(bundle_path: Path) -> bool:
        """
        Validate bundle structure.

        Args:
            bundle_path: Path to bundle (ZIP file or directory)

        Returns:
            True if valid, False otherwise
        """
        try:
            # If it's a directory, check for manifest.yaml directly
            if bundle_path.is_dir():
                manifest_path = bundle_path / "manifest.yaml"
                return manifest_path.exists()
            
            # If it's a ZIP file, check inside the ZIP
            if bundle_path.suffix.lower() == ".zip":
                with zipfile.ZipFile(bundle_path, "r") as zip_ref:
                    namelist = zip_ref.namelist()
                    return "manifest.yaml" in namelist
            
            return False
        except Exception:
            return False

