"""Tests for API key storage and resolution."""

import base64
import json

from nepher import credentials
from nepher.api.client import get_client


def _npcli_file(home):
    return home / ".npcli" / "credentials.json"


def test_no_key():
    assert credentials.resolve_api_key() is None


def test_store_writes_private_file_not_config(isolated_home):
    credentials.store_api_key("nepher_abc")
    assert (isolated_home / ".nepher" / "api_key").read_text(encoding="utf-8") == "nepher_abc"
    assert not (isolated_home / ".nepher" / "config.toml").exists()
    assert credentials.resolve_api_key() == "nepher_abc"


def test_env_var_wins(monkeypatch):
    credentials.store_api_key("nepher_stored")
    monkeypatch.setenv("NEPHER_API_KEY", "nepher_env")
    assert credentials.resolve_api_key() == "nepher_env"


def test_npcli_credentials_are_used(isolated_home):
    path = _npcli_file(isolated_home)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"keyring": False, "api_key": "nepher_npcli"}), encoding="utf-8")
    assert credentials.resolve_api_key() == "nepher_npcli"

    credentials.store_api_key("nepher_own")
    assert credentials.resolve_api_key() == "nepher_own"


def test_legacy_locations_and_cleanup(isolated_home):
    nepher_dir = isolated_home / ".nepher"
    nepher_dir.mkdir()
    (nepher_dir / "config.toml").write_text('api_key = "nepher_cfg"\ncache_dir = "/c"\n', encoding="utf-8")
    assert credentials.resolve_api_key() == "nepher_cfg"

    (nepher_dir / "api_key.enc").write_text(base64.b64encode(b"nepher_enc").decode(), encoding="utf-8")
    assert credentials.resolve_api_key() == "nepher_enc"

    credentials.clear_api_key()
    assert not (nepher_dir / "api_key.enc").exists()
    assert "api_key" not in (nepher_dir / "config.toml").read_text(encoding="utf-8")
    assert "cache_dir" in (nepher_dir / "config.toml").read_text(encoding="utf-8")
    assert credentials.resolve_api_key() is None


def test_client_picks_up_key_changes(monkeypatch):
    assert "X-API-Key" not in get_client().session.headers
    monkeypatch.setenv("NEPHER_API_KEY", "nepher_one")
    assert get_client().session.headers["X-API-Key"] == "nepher_one"
    monkeypatch.setenv("NEPHER_API_KEY", "nepher_two")
    assert get_client().session.headers["X-API-Key"] == "nepher_two"
    monkeypatch.delenv("NEPHER_API_KEY")
    assert "X-API-Key" not in get_client().session.headers
