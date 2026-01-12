"""
Base environment configuration interface.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseEnvCfg(ABC):
    """Base interface for all environment configs (category-agnostic)."""

    name: str = ""
    description: str = ""
    category: str = ""

    @abstractmethod
    def get_terrain_cfg(self) -> Any:
        """Return terrain configuration."""
        pass

    @abstractmethod
    def get_scene_cfg(self) -> Any:
        """Return scene configuration."""
        pass

