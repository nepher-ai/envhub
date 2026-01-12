"""
Config class registry for category-specific configs.
"""

from typing import Dict, Type
from nepher.env_cfgs.base import BaseEnvCfg

# Registry: (category, type) -> config class
_CONFIG_REGISTRY: Dict[tuple[str, str], Type[BaseEnvCfg]] = {}


def get_config_class(category: str, type: str) -> Type[BaseEnvCfg]:
    """
    Get config class for category and type.

    Args:
        category: Environment category
        type: Environment type ("usd" or "preset")

    Returns:
        Config class
    """
    key = (category, type)
    if key not in _CONFIG_REGISTRY:
        # Default to base config if not registered
        from nepher.env_cfgs.base import BaseEnvCfg
        return BaseEnvCfg
    return _CONFIG_REGISTRY[key]


def register_config_class(category: str, type: str, config_class: Type[BaseEnvCfg]):
    """
    Register a custom config class.

    Args:
        category: Environment category
        type: Environment type ("usd" or "preset")
        config_class: Config class to register
    """
    _CONFIG_REGISTRY[(category, type)] = config_class

