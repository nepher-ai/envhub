"""Download environment command."""

from pathlib import Path
from typing import Optional
import click
from nepher.api.client import get_client
from nepher.storage.cache import get_cache_manager
from nepher.storage.bundle import BundleManager
from nepher.cli.utils import print_error, print_success, print_info


@click.command()
@click.argument("env_id")
@click.option("--category", required=True, help="Environment category")
@click.option("--cache-dir", type=click.Path(), help="Override cache directory")
@click.option("--force", is_flag=True, help="Force re-download")
def download(env_id: str, category: str, cache_dir: Optional[str], force: bool):
    """Download an environment."""
    try:
        client = get_client()
        cache_manager = get_cache_manager(
            cache_dir=Path(cache_dir) if cache_dir else None, category=category
        )

        actual_env_id = env_id
        try:
            env_info = client.get_environment(env_id)
            actual_env_id = env_info.get("id", env_id)
        except Exception:
            print_info(f"Searching for environment matching '{env_id}'...")
            envs = client.list_environments(category=category, search=env_id, limit=10)
            
            matches = [e for e in envs if e.get("original_name") == env_id]
            
            if not matches:
                matches = [e for e in envs if env_id.lower() in e.get("original_name", "").lower()]
            
            if not matches:
                print_error(f"Environment '{env_id}' not found in category '{category}'")
                print_info("Use 'nepher list --category navigation' to see available environments")
                return
            
            if len(matches) > 1:
                matches.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
                print_info(f"Found {len(matches)} matches, using most recent: {matches[0].get('id')}")
            
            actual_env_id = matches[0].get("id")
            if not actual_env_id:
                print_error(f"Could not determine environment ID for '{env_id}'")
                return

        if cache_manager.is_cached(actual_env_id) and not force:
            print_info(f"Environment {actual_env_id} is already cached.")
            return

        print_info(f"Downloading {actual_env_id}...")

        cache_path = cache_manager.get_env_cache_path(actual_env_id)
        zip_path = cache_path.parent / f"{actual_env_id}.zip"

        client.download_environment(actual_env_id, zip_path)

        print_info("Extracting bundle...")
        BundleManager.extract_bundle(zip_path, cache_path)

        zip_path.unlink()

        print_success(f"Environment {actual_env_id} downloaded and cached successfully!")

    except Exception as e:
        print_error(f"Failed to download environment: {str(e)}")

