"""Shared fixtures: isolate every test from the real home directory, env vars and keyring."""

import pytest

import nepher.api.client as client_module
import nepher.config as config_module
import nepher.credentials as credentials_module


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.chdir(work)
    for var in ("NEPHER_API_KEY", "NEPHER_CACHE_DIR", "NEPHER_API_URL", "ENVHUB_API_URL", "NEPHER_ENVHUB_API_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(credentials_module, "HAS_KEYRING", False)
    monkeypatch.setattr(
        credentials_module, "_npcli_credentials_file", lambda: home / ".npcli" / "credentials.json"
    )
    monkeypatch.setattr(config_module, "_config_instance", None)
    monkeypatch.setattr(client_module, "_client_instance", None)
    return home
