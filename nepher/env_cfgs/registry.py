"""Config class registry for category-specific configs."""

from typing import Dict, Type
from nepher.env_cfgs.base import BaseEnvCfg

# Registry: (category, type) -> config class
_CONFIG_REGISTRY: Dict[tuple[str, str], Type[BaseEnvCfg]] = {}


def get_config_class(category: str, type: str) -> Type[BaseEnvCfg]:
    """Get config class for category and type."""
    key = (category, type)
    if key not in _CONFIG_REGISTRY:
        # Try to import the category module to trigger registration
        # This ensures that registration code in __init__.py runs
        try:
            if category == "navigation":
                import nepher.env_cfgs.navigation  # noqa: F401  # This will trigger registration
            # Add other categories here as needed
            # elif category == "manipulation":
            #     import nepher.env_cfgs.manipulation
        except ImportError:
            pass  # Category module doesn't exist
        
        # Check again after import
        if key not in _CONFIG_REGISTRY:
            raise ValueError(
                f"No config class registered for category={category}, type={type}. "
                f"Available registrations: {list(_CONFIG_REGISTRY.keys())}"
            )
    return _CONFIG_REGISTRY[key]


def register_config_class(category: str, type: str, config_class: Type[BaseEnvCfg]):
    """Register a custom config class."""
    _CONFIG_REGISTRY[(category, type)] = config_class

