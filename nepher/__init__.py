"""
Nepher: Universal Isaac Lab Environments Platform

A unified, category-agnostic Python package for managing Isaac Lab environments.
"""

__version__ = "0.1.0"

from nepher.config import get_config, set_config
from nepher.auth import login, logout, whoami, get_api_key
from nepher.api.client import get_client, APIClient
from nepher.core import Environment, Scene
from nepher.loader import load_env, load_scene

__all__ = [
    # Version
    "__version__",
    # Configuration
    "get_config",
    "set_config",
    # Authentication
    "login",
    "logout",
    "whoami",
    "get_api_key",
    # API Client
    "get_client",
    "APIClient",
    # Core types
    "Environment",
    "Scene",
    # Loaders
    "load_env",
    "load_scene",
]

