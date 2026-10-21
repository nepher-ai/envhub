"""Cache management commands."""

from pathlib import Path
from typing import Optional

import click

from nepher.cli.utils import print_error, print_info, print_success
from nepher.storage.cache import get_cache_manager

cache_dir_option = click.option("--cache-dir", type=click.Path(), default=None, help="Override cache directory")
category_option = click.option("--category", default=None, help="Use the category-specific cache directory")


def _manager(cache_dir: Optional[str], category: Optional[str]):
    return get_cache_manager(cache_dir=Path(cache_dir) if cache_dir else None, category=category)


@click.group()
def cache():
    """Manage local cache."""
    pass


@cache.command(name="list")
@cache_dir_option
@category_option
def list_cache(cache_dir: Optional[str], category: Optional[str]):
    """List cached environments."""
    try:
        cached = _manager(cache_dir, category).list_cached()
        if not cached:
            print_info("No cached environments.")
            return

        print_info(f"Cached environments ({len(cached)}):")
        for env_id in cached:
            click.echo(f"  {env_id}")

    except Exception as e:
        print_error(f"Failed to list cache: {e}")
        raise SystemExit(1)


@cache.command()
@click.argument("env_id", required=False)
@cache_dir_option
@category_option
def clear(env_id: Optional[str], cache_dir: Optional[str], category: Optional[str]):
    """Clear cache (all cached environments or a specific one)."""
    try:
        manager = _manager(cache_dir, category)
        if env_id:
            if manager.clear_cache(env_id):
                print_success(f"Cleared cache for {env_id}")
            else:
                print_info(f"{env_id} is not cached.")
        else:
            manager.clear_cache()
            print_success("Cleared all cached environments")

    except Exception as e:
        print_error(f"Failed to clear cache: {e}")
        raise SystemExit(1)


@cache.command()
@cache_dir_option
@category_option
def info(cache_dir: Optional[str], category: Optional[str]):
    """Show cache statistics."""
    try:
        stats = _manager(cache_dir, category).get_cache_info()

        print_info("Cache Information:")
        click.echo(f"  Cache Directory: {stats['cache_dir']}")
        click.echo(f"  Total Size: {stats['total_size'] / (1024**2):.2f} MB")
        click.echo(f"  Environment Count: {stats['env_count']}")

        if stats["environments"]:
            click.echo("\n  Environments:")
            for env in stats["environments"]:
                click.echo(f"    {env['id']}: {env['size'] / (1024**2):.2f} MB")

    except Exception as e:
        print_error(f"Failed to get cache info: {e}")
        raise SystemExit(1)


@cache.command()
@click.argument("new_path", type=click.Path())
@cache_dir_option
@category_option
def migrate(new_path: str, cache_dir: Optional[str], category: Optional[str]):
    """Move cached environments to NEW_PATH and make it the configured cache_dir."""
    try:
        _manager(cache_dir, category).migrate_cache(Path(new_path))
        print_success(f"Cache migrated to {Path(new_path).expanduser().resolve()}")

    except Exception as e:
        print_error(f"Failed to migrate cache: {e}")
        raise SystemExit(1)
