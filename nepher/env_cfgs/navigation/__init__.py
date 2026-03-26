"""Navigation environment configuration classes.

- AbstractNavigationEnvCfg: Abstract base with strategy-delegated position generation
- PresetNavigationEnvCfg: Scene description for preset environments (terrain + obstacles + lighting)
- UsdNavigationEnvCfg: USD-based environments with occupancy-map sampling
"""

from nepher.env_cfgs.navigation.abstract_nav_cfg import AbstractNavigationEnvCfg
from nepher.env_cfgs.navigation.preset_nav_cfg import (
    ObstacleConfig,
    PresetNavigationEnvCfg,
)
from nepher.env_cfgs.navigation.usd_nav_cfg import (
    ExclusionZoneConfig,
    SpawnAreaConfig,
    UsdNavigationEnvCfg,
)

from nepher.env_cfgs.registry import register_config_class

register_config_class("navigation", "usd", UsdNavigationEnvCfg)
register_config_class("navigation", "preset", PresetNavigationEnvCfg)

__all__ = [
    "AbstractNavigationEnvCfg",
    "ExclusionZoneConfig",
    "ObstacleConfig",
    "PresetNavigationEnvCfg",
    "SpawnAreaConfig",
    "UsdNavigationEnvCfg",
]
