"""Download environment command."""

import click
from pathlib import Path
from nepher.api.client import get_client
from nepher.storage.cache import get_cache_manager
from nepher.storage.bundle import BundleManager
from nepher.cli.utils import print_error, print_success, print_info


@click.command()
@click.argument("env_id")
@click.option("--category", required=True, help="Environment category")
@click.option("--cache-dir", type=click.Path(), help="Override cache directory")
@click.option("--force", is_flag=True, help="Force re-download")
def download(env_id: str, category: str, cache_dir: str, force: bool):
    """Download an environment."""
    try:
        client = get_client()
        cache_manager = get_cache_manager(
            cache_dir=Path(cache_dir) if cache_dir else None, category=category
        )

        # Check if already cached
        if cache_manager.is_cached(env_id) and not force:
            print_info(f"Environment {env_id} is already cached.")
            return

        print_info(f"Downloading {env_id}...")

        # Download bundle
        cache_path = cache_manager.get_env_cache_path(env_id)
        zip_path = cache_path.parent / f"{env_id}.zip"

        client.download_environment(env_id, zip_path)

        # Extract bundle
        print_info("Extracting bundle...")
        BundleManager.extract_bundle(zip_path, cache_path)

        # Clean up ZIP
        zip_path.unlink()

        print_success(f"Environment {env_id} downloaded and cached successfully!")

    except Exception as e:
        print_error(f"Failed to download environment: {str(e)}")

