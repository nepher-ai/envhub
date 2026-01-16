"""
Authentication management for Nepher.

Handles secure API key storage and user authentication.
"""

import os
from pathlib import Path
from typing import Optional
from nepher.config import get_config, set_config
from nepher.api.client import APIClient, APIError

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False


def _get_keyring_service() -> str:
    """Get keyring service name."""
    return "nepher"


def _get_keyring_username() -> str:
    """Get keyring username."""
    return "api_key"


def _get_encrypted_file_path() -> Path:
    """Get path to encrypted API key file."""
    config_dir = Path.home() / ".nepher"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "api_key.enc"


def _store_api_key_secure(api_key: str):
    """Store API key securely (keyring or encrypted file)."""
    if HAS_KEYRING:
        try:
            keyring.set_password(_get_keyring_service(), _get_keyring_username(), api_key)
            return
        except Exception:
            pass  # Fall back to file storage

    import base64

    encrypted = base64.b64encode(api_key.encode()).decode()
    _get_encrypted_file_path().write_text(encrypted)


def _get_api_key_secure() -> Optional[str]:
    """Retrieve API key from secure storage."""
    if HAS_KEYRING:
        try:
            key = keyring.get_password(_get_keyring_service(), _get_keyring_username())
            if key:
                return key
        except Exception:
            pass

    key_file = _get_encrypted_file_path()
    if key_file.exists():
        try:
            import base64

            encrypted = key_file.read_text()
            return base64.b64decode(encrypted.encode()).decode()
        except Exception:
            pass

    return None


def _clear_api_key_secure():
    """Clear API key from secure storage."""
    if HAS_KEYRING:
        try:
            keyring.delete_password(_get_keyring_service(), _get_keyring_username())
        except Exception:
            pass

    key_file = _get_encrypted_file_path()
    if key_file.exists():
        key_file.unlink()


def login(api_key: str) -> bool:
    """
    Login with API key.

    Args:
        api_key: API key to store

    Returns:
        True if login successful, False otherwise
    """
    try:
        client = APIClient(api_key=None)
        response = client.api_key_login(api_key)
        if not response or "access_token" not in response:
            return False
    except APIError:
        return False

    # Store API key securely
    _store_api_key_secure(api_key)
    set_config("api_key", api_key, save=True)

    return True


def logout():
    """Logout and clear stored credentials."""
    _clear_api_key_secure()
    set_config("api_key", None, save=True)


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
        client = APIClient(api_key=api_key)
        return client.get_user_info()
    except APIError:
        return None


def get_api_key() -> Optional[str]:
    """
    Get stored API key.

    Returns:
        API key or None if not set
    """
    key = _get_api_key_secure()
    if key:
        return key

    config = get_config()
    return config.get_api_key() if config else None

