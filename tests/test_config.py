"""Tests for configuration management."""

import json
from pathlib import Path

import pytest

from nepher.config import DEFAULT_API_URL, Config


def test_config_defaults():
    config = Config()
    assert config.get("api_url") == DEFAULT_API_URL
    assert config.get("cache_dir") is not None


def test_config_get_set():
    config = Config()
    config.set("test_key", "test_value", save=False)
    assert config.get("test_key") == "test_value"


def test_cache_dir_resolution_does_not_create_dir(isolated_home):
    cache_dir = Config().get_cache_dir()
    assert cache_dir == (isolated_home / ".nepher" / "cache").resolve()
    assert not cache_dir.exists()


def test_category_cache_dir(tmp_path):
    config = Config()
    config.set("categories.navigation.cache_dir", str(tmp_path / "nav"), save=False)
    assert config.get_cache_dir(category="navigation") == (tmp_path / "nav").resolve()
    assert config.get_cache_dir(category="manipulation") == config.get_cache_dir()


def test_env_var_precedence(monkeypatch):
    monkeypatch.setenv("NEPHER_API_URL", "https://example.test/")
    assert Config().get_api_url() == "https://example.test/envhub"
    monkeypatch.setenv("ENVHUB_API_URL", "https://envhub.test")
    assert Config().get_api_url() == "https://envhub.test"
    monkeypatch.setenv("NEPHER_ENVHUB_API_URL", "https://nepher-envhub.test")
    assert Config().get_api_url() == "https://nepher-envhub.test"


def test_cache_dir_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("NEPHER_CACHE_DIR", str(tmp_path / "c"))
    assert Config().get("cache_dir") == str(tmp_path / "c")


def test_legacy_api_url_in_file_is_ignored(isolated_home):
    cfg_dir = isolated_home / ".nepher"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").write_text(
        'api_url = "https://envhub-api.nepher.ai"\napi_key = "nepher_old"\ncache_dir = "/data/cache"\n',
        encoding="utf-8",
    )
    config = Config()
    assert config.get_api_url() == DEFAULT_API_URL
    assert config.get("api_key") is None
    assert config.get("cache_dir") == "/data/cache"


def test_custom_api_url_in_file_is_kept(isolated_home):
    cfg_dir = isolated_home / ".nepher"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").write_text('api_url = "https://staging.test/envhub"\n', encoding="utf-8")
    assert Config().get_api_url() == "https://staging.test/envhub"


@pytest.mark.parametrize(
    "content",
    ['cache_dir = "/rc/cache"\n', json.dumps({"cache_dir": "/rc/cache"})],
    ids=["toml", "json"],
)
def test_nepherrc_is_parsed(content):
    Path(".nepherrc").write_text(content, encoding="utf-8")
    assert Config().get("cache_dir") == "/rc/cache"


def test_save_only_writes_explicit_values(isolated_home):
    config = Config()
    config.set("default_category", "navigation")
    saved = (isolated_home / ".nepher" / "config.toml").read_text(encoding="utf-8")
    assert "default_category" in saved
    assert "api_url" not in saved
    assert "cache_dir" not in saved


def test_api_key_cannot_be_set_in_config():
    with pytest.raises(ValueError):
        Config().set("api_key", "nepher_x", save=False)


def test_reset_restores_defaults(isolated_home):
    config = Config()
    config.set("cache_dir", "/somewhere")
    assert config.reset() is True
    assert config.get("cache_dir") == "~/.nepher/cache"
    assert not (isolated_home / ".nepher" / "config.toml").exists()
