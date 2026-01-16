"""Authentication commands."""

import click
from nepher.auth import login as auth_login, logout as auth_logout, whoami as auth_whoami
from nepher.cli.utils import print_success, print_error, print_info


@click.command()
@click.argument("api_key")
def login(api_key: str):
    """Login with API key."""
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
        click.echo(f"  Username: {user_info.get('username', 'N/A')}")
        click.echo(f"  Email: {user_info.get('email', 'N/A')}")
        envhub_role = user_info.get('envhub_role') or user_info.get('role', 'N/A')
        click.echo(f"  Role: {envhub_role}")
        is_active = user_info.get('is_active', True)
        status_text = "Active" if is_active else "Inactive"
        if user_info.get('blocked_until'):
            status_text = f"Blocked until {user_info.get('blocked_until')}"
            if user_info.get('blocked_reason'):
                status_text += f" ({user_info.get('blocked_reason')})"
        click.echo(f"  Status: {status_text}")
    else:
        print_error("Not authenticated. Use 'nepher login <api_key>' to authenticate.")

