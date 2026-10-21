"""
Authentication management for Nepher.

API keys are stored in the system keyring when available, otherwise in
``~/.nepher/api_key`` with owner-only permissions. Keys from ``npcli login``
and ``NEPHER_API_KEY`` are picked up automatically.
"""

from typing import Optional

from nepher.api.client import APIClient, APIError, reset_client
from nepher.api.endpoints import APIEndpoints
from nepher.credentials import clear_api_key, resolve_api_key, store_api_key

API_KEY_PREFIX = "nepher_"


def login(api_key: str) -> bool:
    """
    Validate and store an API key.

    Args:
        api_key: API key (must start with ``nepher_``)

    Returns:
        True if login successful, False if the key does not start with ``nepher_``.

    Raises:
        APIError: The key was rejected or the API could not be reached. The
            message includes the server's reason and the URL that was called.
    """
    api_key = api_key.strip()
    if not api_key.startswith(API_KEY_PREFIX):
        return False

    client = APIClient(api_key=api_key)
    url = f"{client.api_url}{APIEndpoints.API_KEY_LOGIN}"
    try:
        result = client.api_key_login(api_key)
    except APIError as exc:
        raise APIError(f"{exc} ({url})", status_code=exc.status_code) from exc
    if not isinstance(result, dict) or "access_token" not in result:
        raise APIError(f"Unexpected login response ({url})")

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
        User info dictionary, or None when no API key is available.

    Raises:
        APIError: A key is configured but the API rejected it or could not be reached.
    """
    api_key = get_api_key()
    if not api_key:
        return None

    result = APIClient(api_key=api_key).api_key_login(api_key)
    user = result.get("user") if isinstance(result, dict) else None
    return user if isinstance(user, dict) else None


def get_api_key() -> Optional[str]:
    """Get the API key that requests will use, or None if not set."""
    return resolve_api_key()
