"""
Base environment configuration interface.
"""

from typing import Any


class BaseEnvCfg:
    """Base interface for all environment configs (category-agnostic).
    
    Note: Not using ABC to avoid pickling issues with @configclass decorator.
    Subclasses should override methods and raise NotImplementedError if not implemented.
    """

    name: str = ""
    description: str = ""
    category: str = ""

    def get_terrain_cfg(self) -> Any:
        """Return terrain configuration.
        
        Subclasses must override this method.
        """
        raise NotImplementedError("Subclass must implement get_terrain_cfg()")

    def get_scene_cfg(self) -> Any:
        """Return scene configuration.
        
        Subclasses must override this method.
        """
        raise NotImplementedError("Subclass must implement get_scene_cfg()")

