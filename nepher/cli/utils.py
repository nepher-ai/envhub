"""CLI utility functions."""

import click
from rich.console import Console
from rich import print as rprint

console = Console()


def print_success(message: str):
    """Print success message."""
    rprint(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message."""
    rprint(f"[red]✗[/red] {message}")


def print_info(message: str):
    """Print info message."""
    rprint(f"[blue]ℹ[/blue] {message}")


def print_warning(message: str):
    """Print warning message."""
    rprint(f"[yellow]⚠[/yellow] {message}")

