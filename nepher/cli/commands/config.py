"""Configuration management commands."""

import click
from nepher.config import get_config, set_config
from nepher.cli.utils import print_error, print_success, print_info


@click.group()
def config():
    """Manage configuration."""
    pass


@config.command()
@click.argument("key")
def get(key: str):
    """Get configuration value."""
    try:
        value = get_config().get(key)
        if value is None:
            print_error(f"Configuration key '{key}' not found.")
        else:
            click.echo(value)

    except Exception as e:
        print_error(f"Failed to get config: {str(e)}")


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str):
    """Set configuration value."""
    try:
        # Try to parse as appropriate type
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "", 1).isdigit():
            value = float(value)

        set_config(key, value, save=True)
        print_success(f"Set {key} = {value}")

    except Exception as e:
        print_error(f"Failed to set config: {str(e)}")


@config.command()
def list():
    """List all configuration values."""
    try:
        config = get_config()
        print_info("Configuration:")
        click.echo(f"  api_url: {config.get('api_url')}")
        click.echo(f"  cache_dir: {config.get('cache_dir')}")
        click.echo(f"  default_category: {config.get('default_category')}")

    except Exception as e:
        print_error(f"Failed to list config: {str(e)}")


@config.command()
def reset():
    """Reset configuration to defaults."""
    try:
        # Clear config file
        config_file = get_config()._config_file
        if config_file and config_file.exists():
            config_file.unlink()
            print_success("Configuration reset to defaults.")
        else:
            print_info("No configuration file to reset.")

    except Exception as e:
        print_error(f"Failed to reset config: {str(e)}")

