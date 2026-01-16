"""Config class registry for category-specific configs."""

from typing import Dict, Type
from nepher.env_cfgs.base import BaseEnvCfg

# Registry: (category, type) -> config class
_CONFIG_REGISTRY: Dict[tuple[str, str], Type[BaseEnvCfg]] = {}  # type: ignore


def get_config_class(category: str, type: str) -> Type[BaseEnvCfg]:
    """Get config class for category and type."""
    key = (category, type)
    if key not in _CONFIG_REGISTRY:
        try:
            if category == "navigation":
                import nepher.env_cfgs.navigation  # noqa: F401
        except ImportError:
            pass
        
        if key not in _CONFIG_REGISTRY:
            raise ValueError(
                f"No config class registered for category={category}, type={type}. "
                f"Available registrations: {list(_CONFIG_REGISTRY.keys())}"
            )
    return _CONFIG_REGISTRY[key]


def register_config_class(category: str, type: str, config_class: Type[BaseEnvCfg]):
    """Register a custom config class."""
    _CONFIG_REGISTRY[(category, type)] = config_class

