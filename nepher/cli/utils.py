"""CLI utility functions."""

import sys
import click
from rich.console import Console
from rich import print as rprint

console = Console()

# Use ASCII fallbacks on terminals that can't handle Unicode symbols
_can_unicode = sys.stdout.encoding and sys.stdout.encoding.lower().startswith("utf")
_SYM_SUCCESS = "✓" if _can_unicode else "[ok]"
_SYM_ERROR = "✗" if _can_unicode else "[error]"
_SYM_INFO = "ℹ" if _can_unicode else "[info]"
_SYM_WARNING = "⚠" if _can_unicode else "[warn]"


def print_success(message: str):
    """Print success message."""
    rprint(f"[green]{_SYM_SUCCESS}[/green] {message}")


def print_error(message: str):
    """Print error message."""
    rprint(f"[red]{_SYM_ERROR}[/red] {message}")


def print_info(message: str):
    """Print info message."""
    rprint(f"[blue]{_SYM_INFO}[/blue] {message}")


def print_warning(message: str):
    """Print warning message."""
    rprint(f"[yellow]{_SYM_WARNING}[/yellow] {message}")

