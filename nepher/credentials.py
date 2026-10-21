"""
API key storage and resolution.

Resolution order (first hit wins):
1. ``NEPHER_API_KEY`` environment variable
2. Key stored by ``nepher login`` (system keyring, else ``~/.nepher/api_key``)
3. Key stored by ``npcli login`` (keyring service ``npcli`` / ``credentials.json``)
4. Legacy locations written by older releases (``api_key.enc``, ``api_key`` in config.toml)
"""

import base64
import json
import os
from pathlib import Path
from typing import Optional

try:
    import keyring

    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

KEYRING_SERVICE = "nepher"
KEYRING_USERNAME = "api_key"
NPCLI_KEYRING_SERVICE = "npcli"


def _nepher_dir() -> Path:
    return Path.home() / ".nepher"


def _key_file() -> Path:
    return _nepher_dir() / "api_key"


def _legacy_key_file() -> Path:
    return _nepher_dir() / "api_key.enc"


def _npcli_credentials_file() -> Path:
    try:
        from platformdirs import user_config_dir

        return Path(user_config_dir("nepher", appauthor=False)) / "credentials.json"
    except ImportError:
        return _nepher_dir() / "credentials.json"


def _keyring_get(service: str, username: str) -> Optional[str]:
    if not HAS_KEYRING:
        return None
    try:
        return keyring.get_password(service, username) or None
    except Exception:
        return None


def _read_text(path: Path) -> Optional[str]:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _write_private(path: Path, text: str) -> None:
    """Write a file readable only by the current user."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _stored_nepher_key() -> Optional[str]:
    return _keyring_get(KEYRING_SERVICE, KEYRING_USERNAME) or _read_text(_key_file())


def _stored_npcli_key() -> Optional[str]:
    path = _npcli_credentials_file()
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict):
        return None
    if meta.get("keyring"):
        return _keyring_get(NPCLI_KEYRING_SERVICE, "api_key")
    key = meta.get("api_key")
    return key if isinstance(key, str) and key else None


def _legacy_key() -> Optional[str]:
    encoded = _read_text(_legacy_key_file())
    if encoded:
        try:
            return base64.b64decode(encoded.encode()).decode() or None
        except (ValueError, UnicodeDecodeError):
            pass
    config_file = _nepher_dir() / "config.toml"
    try:
        from nepher.config import tomllib

        data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    key = data.get("api_key")
    return key if isinstance(key, str) and key else None


def resolve_api_key() -> Optional[str]:
    """Return the API key to use for requests, or None when not authenticated."""
    return (
        os.getenv("NEPHER_API_KEY")
        or _stored_nepher_key()
        or _stored_npcli_key()
        or _legacy_key()
    )


def _remove_legacy_config_key() -> None:
    from nepher.config import get_config

    config = get_config()
    config_file = getattr(config, "_config_file", None)
    if config_file is None or not config_file.exists():
        return
    try:
        from nepher.config import _load_file

        data = _load_file(config_file)
    except Exception:
        return
    if "api_key" in data:
        config._save_config()


def store_api_key(api_key: str) -> None:
    """Persist an API key: keyring when available, else a 0600 file."""
    stored = False
    if HAS_KEYRING:
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)
            stored = True
        except Exception:
            stored = False

    if stored:
        _key_file().unlink(missing_ok=True)
    else:
        _write_private(_key_file(), api_key)

    _legacy_key_file().unlink(missing_ok=True)
    _remove_legacy_config_key()


def clear_api_key() -> None:
    """Remove every API key stored by ``nepher`` (npcli credentials are left alone)."""
    if HAS_KEYRING:
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except Exception:
            pass
    _key_file().unlink(missing_ok=True)
    _legacy_key_file().unlink(missing_ok=True)
    _remove_legacy_config_key()
