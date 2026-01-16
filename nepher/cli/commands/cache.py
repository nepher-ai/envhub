"""Cache management commands."""

import click
from pathlib import Path
from typing import Optional
from nepher.storage.cache import get_cache_manager
from nepher.cli.utils import print_error, print_success, print_info


@click.group()
def cache():
    """Manage local cache."""
    pass


@cache.command()
def list():
    """List cached environments."""
    try:
        cache_manager = get_cache_manager()
        cached = cache_manager.list_cached()

        if not cached:
            print_info("No cached environments.")
            return

        print_info(f"Cached environments ({len(cached)}):")
        for env_id in cached:
            click.echo(f"  {env_id}")

    except Exception as e:
        print_error(f"Failed to list cache: {str(e)}")


@cache.command()
@click.argument("env_id", required=False)
def clear(env_id: Optional[str]):
    """Clear cache (all or specific environment)."""
    try:
        cache_manager = get_cache_manager()
        if env_id:
            cache_manager.clear_cache(env_id)
            print_success(f"Cleared cache for {env_id}")
        else:
            cache_manager.clear_cache()
            print_success("Cleared all cache")

    except Exception as e:
        print_error(f"Failed to clear cache: {str(e)}")


@cache.command()
def info():
    """Show cache statistics."""
    try:
        cache_manager = get_cache_manager()
        info = cache_manager.get_cache_info()

        print_info("Cache Information:")
        click.echo(f"  Cache Directory: {info['cache_dir']}")
        click.echo(f"  Total Size: {info['total_size'] / (1024**2):.2f} MB")
        click.echo(f"  Environment Count: {info['env_count']}")

        if info["environments"]:
            click.echo("\n  Environments:")
            for env in info["environments"]:
                click.echo(f"    {env['id']}: {env['size'] / (1024**2):.2f} MB")

    except Exception as e:
        print_error(f"Failed to get cache info: {str(e)}")


@cache.command()
@click.argument("new_path", type=click.Path())
def migrate(new_path: str):
    """Migrate cache to new location."""
    try:
        cache_manager = get_cache_manager()
        new_cache_dir = Path(new_path)
        cache_manager.migrate_cache(new_cache_dir)
        print_success(f"Cache migrated to {new_path}")

    except Exception as e:
        print_error(f"Failed to migrate cache: {str(e)}")

