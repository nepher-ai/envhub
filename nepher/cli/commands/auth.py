"""Authentication commands."""

import click
from nepher.auth import login as auth_login, logout as auth_logout, whoami as auth_whoami
from nepher.cli.utils import print_success, print_error, print_info


@click.command()
@click.option(
    "--api-key",
    default=None,
    help="API key (prefer omitting and entering at prompt to avoid history).",
)
def login(api_key: str | None):
    """Login with API key.

    If --api-key is not given, you will be prompted to enter it (recommended:
    key is not stored in shell history).
    """
    if not api_key:
        api_key = click.prompt("API key", hide_input=True)
    if not api_key or not api_key.strip():
        print_error("No API key provided.")
        return
    api_key = api_key.strip()
    if auth_login(api_key):
        print_success("Login successful!")
    else:
        print_error("Login failed. Please check your API key.")


@click.command()
def logout():
    """Logout and clear credentials."""
    auth_logout()
    print_success("Logged out successfully.")


@click.command()
def whoami():
    """Show current user information."""
    user_info = auth_whoami()
    if user_info:
        print_info("Current user:")
        click.echo(f"  Fullname: {user_info.get('fullname', 'N/A')}")
        click.echo(f"  Email: {user_info.get('email', 'N/A')}")
        click.echo(f"  Role: {user_info.get('role', 'N/A')}")
        click.echo(f"  Status: {user_info.get('status', 'N/A')}")
    else:
        print_error("Not authenticated. Use 'nepher login' to authenticate.")

