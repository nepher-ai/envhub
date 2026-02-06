"""Configuration management commands."""

from typing import Any

import click
from nepher.config import get_config, set_config
from nepher.cli.utils import print_error, print_success, print_info


@click.group()
def config():
    """Manage configuration."""
    pass


def _mask_secret(key: str, value: Any) -> Any:
    """Mask secret keys so they are never echoed in full."""
    if value is None or not isinstance(value, str):
        return value
    lower = key.lower()
    if "api_key" in lower or "secret" in lower or "password" in lower or "token" in lower:
        if len(value) < 8:
            return "***"
        return f"{value[:4]}...{value[-4:]}"
    return value


@config.command()
@click.argument("key")
def get(key: str):
    """Get configuration value (secrets are masked)."""
    try:
        value = get_config().get(key)
        if value is None:
            print_error(f"Configuration key '{key}' not found.")
        else:
            display = _mask_secret(key, value)
            click.echo(display)

    except Exception as e:
        print_error(f"Failed to get config: {str(e)}")


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str):
    """Set configuration value."""
    try:
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "", 1).isdigit():
            value = float(value)

        set_config(key, value, save=True)
        display = _mask_secret(key, value) if isinstance(value, str) else value
        print_success(f"Set {key} = {display}")

    except Exception as e:
        print_error(f"Failed to set config: {str(e)}")


@config.command()
def list():
    """List all configuration values."""
    try:
        cfg = get_config()
        print_info("Configuration:")
        click.echo(f"  api_url: {cfg.get('api_url')}")
        click.echo(f"  cache_dir: {cfg.get('cache_dir')}")
        click.echo(f"  default_category: {cfg.get('default_category')}")

    except Exception as e:
        print_error(f"Failed to list config: {str(e)}")


@config.command()
def reset():
    """Reset configuration to defaults."""
    try:
        config = get_config()
        config_file = getattr(config, "_config_file", None)
        if config_file and config_file.exists():
            config_file.unlink()
            print_success("Configuration reset to defaults.")
        else:
            print_info("No configuration file to reset.")

    except Exception as e:
        print_error(f"Failed to reset config: {str(e)}")

