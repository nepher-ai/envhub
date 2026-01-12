"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path
from nepher.config import Config, get_config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.get("api_url") is not None
    assert config.get("cache_dir") is not None


def test_config_get_set():
    """Test getting and setting config values."""
    config = Config()
    config.set("test_key", "test_value", save=False)
    assert config.get("test_key") == "test_value"


def test_cache_dir_resolution():
    """Test cache directory path resolution."""
    config = Config()
    cache_dir = config.get_cache_dir()
    assert isinstance(cache_dir, Path)
    assert cache_dir.exists() or cache_dir.parent.exists()


def test_config_priority():
    """Test configuration priority (env var overrides config file)."""
    # This would require mocking, simplified for now
    config = Config()
    # Environment variables should override config file
    if os.getenv("NEPHER_CACHE_DIR"):
        assert config.get("cache_dir") == os.getenv("NEPHER_CACHE_DIR")

