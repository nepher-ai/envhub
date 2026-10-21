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


def _parse_value(value: str) -> Any:
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.isdigit():
        return int(value)
    if value.replace(".", "", 1).isdigit():
        return float(value)
    return value


@config.command()
@click.argument("key")
def get(key: str):
    """Get configuration value (secrets are masked)."""
    value = get_config().get(key)
    if value is None:
        print_error(f"Configuration key '{key}' not found.")
        raise SystemExit(1)
    click.echo(_mask_secret(key, value))


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def set_value(key: str, value: str):
    """Set configuration value."""
    try:
        parsed = _parse_value(value)
        set_config(key, parsed, save=True)
        display = _mask_secret(key, parsed) if isinstance(parsed, str) else parsed
        print_success(f"Set {key} = {display}")
    except Exception as e:
        print_error(f"Failed to set config: {e}")
        raise SystemExit(1)


@config.command(name="list")
def list_values():
    """List configuration values."""
    cfg = get_config()
    print_info("Configuration:")
    click.echo(f"  api_url: {cfg.get('api_url')}")
    click.echo(f"  cache_dir: {cfg.get('cache_dir')}")
    click.echo(f"  default_category: {cfg.get('default_category')}")


@config.command()
def reset():
    """Reset configuration to defaults (stored API key is not affected)."""
    try:
        if get_config().reset():
            print_success("Configuration reset to defaults.")
        else:
            print_info("No configuration file to reset.")
    except Exception as e:
        print_error(f"Failed to reset config: {e}")
        raise SystemExit(1)
