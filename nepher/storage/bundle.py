"""
Bundle validation and extraction.
"""

import shutil
import tempfile
import zipfile
from pathlib import Path

from nepher.core import Environment
from nepher.storage.manifest import ManifestParser
from nepher.storage.paths import resolve_within

# Skipped when zipping a bundle directory for upload.
EXCLUDED_NAMES = {".git", ".hg", ".svn", "__pycache__", ".DS_Store", ".env", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def safe_extract(zip_path: Path, dest_dir: Path) -> None:
    """Extract ``zip_path`` into ``dest_dir``, rejecting unsafe or oversized archives."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        dest_dir.mkdir(parents=True, exist_ok=True)

        total = 0
        for member in members:
            resolve_within(dest_dir, member.filename)
            total += member.file_size

        free = shutil.disk_usage(dest_dir).free
        if total > free:
            raise ValueError(
                f"Bundle needs {total / 1024**3:.2f} GB but only {free / 1024**3:.2f} GB is free in {dest_dir}"
            )

        zf.extractall(dest_dir, members=members)


def iter_bundle_files(bundle_dir: Path):
    """Yield files to include when zipping a bundle directory."""
    for path in sorted(bundle_dir.rglob("*")):
        rel = path.relative_to(bundle_dir)
        if any(part in EXCLUDED_NAMES for part in rel.parts):
            continue
        if path.is_file() and path.suffix not in EXCLUDED_SUFFIXES:
            yield path, rel


class BundleManager:
    """Manages environment bundle operations."""

    @staticmethod
    def extract_bundle(zip_path: Path, dest_dir: Path) -> Environment:
        """
        Extract and validate bundle.

        Extraction happens in a staging directory next to ``dest_dir`` and is
        moved into place only after the manifest parses, so a failed or
        interrupted extraction never leaves a half-populated cache entry.

        Args:
            zip_path: Path to bundle ZIP file
            dest_dir: Destination directory for extraction

        Returns:
            Environment object from manifest
        """
        dest_dir = Path(dest_dir)
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{dest_dir.name}.", dir=dest_dir.parent))

        try:
            try:
                safe_extract(zip_path, staging)
            except zipfile.BadZipFile as e:
                raise ValueError(f"Invalid ZIP file: {zip_path}") from e
            except (PermissionError, OSError) as e:
                raise RuntimeError(f"Cannot extract bundle to {dest_dir}: {e}") from e

            manifest_path = staging / "manifest.yaml"
            if not manifest_path.is_file():
                raise ValueError("Manifest not found at the root of the bundle")
            ManifestParser.parse(manifest_path)

            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            staging.rename(dest_dir)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

        return ManifestParser.parse(dest_dir / "manifest.yaml")

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
                return (bundle_path / "manifest.yaml").is_file()

            if bundle_path.suffix.lower() == ".zip":
                with zipfile.ZipFile(bundle_path, "r") as zip_ref:
                    return "manifest.yaml" in zip_ref.namelist()

            return False
        except (OSError, zipfile.BadZipFile):
            return False
