"""
Authentication management for Nepher.

API keys are stored in the system keyring when available, otherwise in
``~/.nepher/api_key`` with owner-only permissions. Keys from ``npcli login``
and ``NEPHER_API_KEY`` are picked up automatically.
"""

from typing import Optional

from nepher.api.client import APIClient, APIError, reset_client
from nepher.credentials import clear_api_key, resolve_api_key, store_api_key

API_KEY_PREFIX = "nepher_"


def login(api_key: str) -> bool:
    """
    Validate and store an API key.

    Args:
        api_key: API key (must start with ``nepher_``)

    Returns:
        True if login successful, False otherwise
    """
    api_key = api_key.strip()
    if not api_key.startswith(API_KEY_PREFIX):
        return False

    try:
        APIClient(api_key=api_key).get_user_info()
    except APIError:
        return False

    store_api_key(api_key)
    reset_client()
    return True


def logout():
    """Clear credentials stored by ``nepher login``."""
    clear_api_key()
    reset_client()


def whoami() -> Optional[dict]:
    """
    Get current user information.

    Returns:
        User info dictionary or None if not authenticated
    """
    api_key = get_api_key()
    if not api_key:
        return None

    try:
        return APIClient(api_key=api_key).get_user_info()
    except APIError:
        return None


def get_api_key() -> Optional[str]:
    """Get the API key that requests will use, or None if not set."""
    return resolve_api_key()
