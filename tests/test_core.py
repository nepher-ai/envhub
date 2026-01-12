"""Tests for core data structures."""

from pathlib import Path
from nepher.core import Environment, Scene


def test_environment_creation():
    """Test creating an environment."""
    env = Environment(
        id="test-env",
        name="Test Environment",
        category="navigation",
    )
    assert env.id == "test-env"
    assert env.name == "Test Environment"
    assert env.category == "navigation"


def test_scene_creation():
    """Test creating a scene."""
    scene = Scene(name="test-scene", usd=Path("/path/to/scene.usd"))
    assert scene.name == "test-scene"
    assert scene.usd is not None


def test_environment_get_scene():
    """Test getting scene from environment."""
    env = Environment(
        id="test-env",
        name="Test Environment",
        scenes=[Scene(name="scene1"), Scene(name="scene2")],
    )
    scene = env.get_scene("scene1")
    assert scene is not None
    assert scene.name == "scene1"

    scene_by_index = env.get_scene(0)
    assert scene_by_index is not None
    assert scene_by_index.name == "scene1"

