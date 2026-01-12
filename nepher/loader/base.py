"""
Base loader interface.
"""

from abc import ABC, abstractmethod
from nepher.core import Environment
from nepher.env_cfgs.base import BaseEnvCfg


class BaseLoader(ABC):
    """Base interface for environment loaders."""

    @abstractmethod
    def load(self, env: Environment, scene_idx: int, category: str) -> BaseEnvCfg:
        """
        Load scene config.

        Args:
            env: Environment object
            scene_idx: Scene index
            category: Environment category

        Returns:
            Category-appropriate config class
        """
        pass

