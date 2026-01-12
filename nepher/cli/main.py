"""
Main CLI entry point.
"""

import click
from nepher.cli.commands import auth, list_cmd, download, upload, cache, view, config


@click.group()
@click.version_option()
def main():
    """Nepher: Universal Isaac Lab Environments Platform."""
    pass


# Register commands
main.add_command(auth.login)
main.add_command(auth.logout)
main.add_command(auth.whoami)
main.add_command(list_cmd.list_cmd)
main.add_command(download.download)
main.add_command(upload.upload)
main.add_command(cache.cache)
main.add_command(view.view)
main.add_command(config.config)


if __name__ == "__main__":
    main()

