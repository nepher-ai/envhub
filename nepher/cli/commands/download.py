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

        # Try to find the environment - first by exact ID, then by name search
        actual_env_id = env_id
        try:
            # Try to get by exact ID first
            env_info = client.get_environment(env_id)
            actual_env_id = env_info.get("id", env_id)
        except Exception:
            # If exact ID fails, search by name
            print_info(f"Searching for environment matching '{env_id}'...")
            envs = client.list_environments(category=category, search=env_id, limit=10)
            
            # Filter by exact name match (original_name)
            matches = [e for e in envs if e.get("original_name") == env_id]
            
            if not matches:
                # If no exact match, try partial matches
                matches = [e for e in envs if env_id.lower() in e.get("original_name", "").lower()]
            
            if not matches:
                print_error(f"Environment '{env_id}' not found in category '{category}'")
                print_info("Use 'nepher list --category navigation' to see available environments")
                return
            
            if len(matches) > 1:
                # Multiple matches - use the most recent one
                matches.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
                print_info(f"Found {len(matches)} matches, using most recent: {matches[0].get('id')}")
            
            actual_env_id = matches[0].get("id")
            if not actual_env_id:
                print_error(f"Could not determine environment ID for '{env_id}'")
                return

        # Check if already cached (using original name for cache key)
        if cache_manager.is_cached(env_id) and not force:
            print_info(f"Environment {env_id} is already cached.")
            return

        print_info(f"Downloading {env_id}...")

        # Download bundle
        cache_path = cache_manager.get_env_cache_path(env_id)
        zip_path = cache_path.parent / f"{env_id}.zip"

        client.download_environment(actual_env_id, zip_path)

        # Extract bundle
        print_info("Extracting bundle...")
        BundleManager.extract_bundle(zip_path, cache_path)

        # Clean up ZIP
        zip_path.unlink()

        print_success(f"Environment {env_id} downloaded and cached successfully!")

    except Exception as e:
        print_error(f"Failed to download environment: {str(e)}")

