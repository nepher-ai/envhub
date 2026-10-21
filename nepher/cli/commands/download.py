"""Download environment command."""

from pathlib import Path
from typing import Optional

import click

from nepher.api.client import APIClient, APIError, get_client
from nepher.cli.utils import print_error, print_info, print_success
from nepher.storage.bundle import BundleManager
from nepher.storage.cache import get_cache_manager
from nepher.storage.paths import safe_env_id


def _resolve_by_name(client: APIClient, name: str, category: Optional[str]) -> Optional[dict]:
    """Find an environment whose ID or name matches ``name`` exactly (newest wins)."""
    envs = client.list_environments(category=category, search=name, limit=50)
    matches = [e for e in envs if name in (e.get("id"), e.get("original_name"), e.get("name"))]
    if not matches:
        suggestions = [e.get("id") for e in envs if e.get("id")][:5]
        if suggestions:
            print_info("Did you mean: " + ", ".join(suggestions))
        return None
    if len(matches) > 1:
        matches.sort(key=lambda e: e.get("uploaded_at") or "", reverse=True)
        print_info(f"Found {len(matches)} environments named '{name}', using most recent: {matches[0].get('id')}")
    return matches[0]


@click.command()
@click.argument("env_id")
@click.option("--category", default=None, help="Environment category (optional, resolved automatically)")
@click.option("--cache-dir", type=click.Path(), help="Override cache directory")
@click.option("--force", is_flag=True, help="Force re-download")
@click.option(
    "--api-key",
    default=None,
    envvar="NEPHER_API_KEY",
    help="API key for authentication. Sent directly so downloads succeed "
    "regardless of any access-token expiry.",
)
def download(env_id: str, category: Optional[str], cache_dir: Optional[str], force: bool, api_key: Optional[str]):
    """Download an environment by ID or exact name."""
    try:
        client = get_client(api_key=api_key)

        try:
            env_info = client.get_environment(env_id)
        except APIError as e:
            if e.status_code != 404:
                raise
            print_info(f"No environment with ID '{env_id}', searching by name...")
            env_info = _resolve_by_name(client, env_id, category)
            if env_info is None:
                msg = f"Environment '{env_id}' not found"
                if category:
                    msg += f" in category '{category}'"
                print_error(msg)
                print_info("Use 'nepher list' to see available environments")
                raise SystemExit(1)

        actual_env_id = safe_env_id(str(env_info.get("id") or env_id))
        resolved_category = category or env_info.get("category")

        cache_manager = get_cache_manager(
            cache_dir=Path(cache_dir) if cache_dir else None, category=resolved_category
        )

        if cache_manager.is_cached(actual_env_id) and not force:
            print_info(f"Environment {actual_env_id} is already cached at {cache_manager.get_env_cache_path(actual_env_id)}")
            return

        print_info(f"Downloading {actual_env_id}...")
        cache_path = cache_manager.get_env_cache_path(actual_env_id)
        zip_path = cache_path.parent / f".{actual_env_id}.zip"

        try:
            client.download_environment(actual_env_id, zip_path)
            print_info("Extracting bundle...")
            BundleManager.extract_bundle(zip_path, cache_path)
        finally:
            zip_path.unlink(missing_ok=True)

        print_success(f"Environment {actual_env_id} downloaded and cached at {cache_path}")

    except SystemExit:
        raise
    except Exception as e:
        print_error(f"Failed to download environment: {e}")
        raise SystemExit(1)
