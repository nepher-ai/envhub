"""Environment configuration definitions for navigation environments.

This module provides base classes for creating navigation environment configurations:

- AbstractNavigationEnvCfg: Abstract base class for all navigation environments
- PresetNavigationEnvCfg: Base class for preset environments with obstacle definitions
- ObstacleConfig: Configuration dataclass for individual obstacles
- UsdNavigationEnvCfg: Base class for USD-based environments loaded from scene files
- SpawnAreaConfig: Configuration dataclass for spawn areas in USD environments
- ExclusionZoneConfig: Configuration dataclass for exclusion zones in USD environments
"""

from nepher.env_cfgs.navigation.abstract_nav_cfg import (
    AbstractNavigationEnvCfg,
    AbstractEnvironmentCfg,  # Alias for backward compatibility
)
from nepher.env_cfgs.navigation.preset_nav_cfg import (
    ObstacleConfig,
    PresetNavigationEnvCfg,
    ObstacleEnvironmentPresetCfg,  # Alias for backward compatibility
)
from nepher.env_cfgs.navigation.usd_nav_cfg import (
    ExclusionZoneConfig,
    SpawnAreaConfig,
    UsdNavigationEnvCfg,
    UsdEnvironmentCfg,  # Alias for backward compatibility
)

# Register config classes in the registry
from nepher.env_cfgs.registry import register_config_class

register_config_class("navigation", "usd", UsdNavigationEnvCfg)
register_config_class("navigation", "preset", PresetNavigationEnvCfg)

__all__ = [
    "AbstractNavigationEnvCfg",
    "AbstractEnvironmentCfg",  # Backward compatibility alias
    "ExclusionZoneConfig",
    "ObstacleConfig",
    "ObstacleEnvironmentPresetCfg",  # Backward compatibility alias
    "PresetNavigationEnvCfg",
    "SpawnAreaConfig",
    "UsdEnvironmentCfg",  # Backward compatibility alias
    "UsdNavigationEnvCfg",
]
