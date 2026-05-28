# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""USD-based navigation environment configuration.

The terrain, obstacles, and scene elements live in a USD file.
Position generation is handled by an ``OccupancySamplerStrategy``
auto-wired in ``__post_init__`` from spawn-area / occupancy-map config.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.terrains import TerrainImporterCfg
from isaaclab.utils import configclass

from nepher.env_cfgs.navigation.abstract_nav_cfg import AbstractNavigationEnvCfg
from nepher.utils.fast_spawn_sampler import OccupancyMapConfig
from nepher.utils.strategies.occupancy_sampler import OccupancySamplerStrategy


@dataclass
class SpawnAreaConfig:
    """Rectangular region safe for robot / goal spawning."""

    bounds: tuple[float, float, float, float] = (-1.0, -1.0, 1.0, 1.0)
    """``(x_min, y_min, x_max, y_max)`` in world coordinates."""

    weight: float = 1.0
    """Relative sampling weight (higher = more likely)."""

    name: str = ""
    """Optional human-readable label."""

    @property
    def x_min(self) -> float:
        return self.bounds[0]

    @property
    def y_min(self) -> float:
        return self.bounds[1]

    @property
    def x_max(self) -> float:
        return self.bounds[2]

    @property
    def y_max(self) -> float:
        return self.bounds[3]

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)


@dataclass
class ExclusionZoneConfig:
    """Rectangular region that must be avoided for spawning."""

    bounds: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    """``(x_min, y_min, x_max, y_max)`` in world coordinates."""

    name: str = ""
    """Optional human-readable label."""

    @property
    def x_min(self) -> float:
        return self.bounds[0]

    @property
    def y_min(self) -> float:
        return self.bounds[1]

    @property
    def x_max(self) -> float:
        return self.bounds[2]

    @property
    def y_max(self) -> float:
        return self.bounds[3]


@configclass
class UsdNavigationEnvCfg(AbstractNavigationEnvCfg):
    """Configuration for USD-based navigation environments.

    An ``OccupancySamplerStrategy`` is auto-wired in ``__post_init__`` from
    ``spawn_areas``, ``exclusion_zones``, and ``occupancy_map_yaml``.
    """

    name: str = "usd_env"
    description: str = "Base USD environment loaded from a scene file"
    category: str = "navigation"

    # ========== USD Scene ==========

    usd_path: str = ""
    usd_scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    usd_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    usd_rotation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)

    # ========== Terrain ==========

    terrain_type: str = "usd"
    """``'usd'`` to load from ``usd_path``, ``'plane'`` for flat ground."""

    terrain_friction: float = 1.0
    terrain_restitution: float = 0.0
    env_spacing: float = 50.0

    # ========== Spawn / Exclusion ==========

    spawn_areas: list[SpawnAreaConfig] = field(default_factory=list)
    exclusion_zones: list[ExclusionZoneConfig] = field(default_factory=list)

    playground: tuple[float, float, float, float] | None = None
    """Explicit playground bounds. ``None`` = computed from spawn areas."""

    robot_safety_margin: float = 0.25
    spawn_area_margin: float = 0.1
    robot_init_yaw_range: tuple[float, float] = (-math.pi, math.pi)

    # ========== Occupancy Sampler ==========

    occupancy_map_yaml: str | None = None
    """ROS-style occupancy-map YAML for collision-free sampling."""

    spawn_grid_resolution: float = 0.1

    # ========== Lighting ==========

    use_usd_lighting: bool = True
    sky_light_intensity: float = 750.0
    sky_texture: str | None = None
    sky_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    sky_visible: bool = True

    # ========== Auto-wire strategy ==========

    def __post_init__(self):
        omap_cfg = None
        if self.occupancy_map_yaml:
            omap_cfg = OccupancyMapConfig(
                yaml_path=self.occupancy_map_yaml,
                safety_margin=self.robot_safety_margin,
            )

        spawn_bounds = None
        if self.spawn_areas:
            spawn_bounds = (
                min(a.x_min for a in self.spawn_areas),
                min(a.y_min for a in self.spawn_areas),
                max(a.x_max for a in self.spawn_areas),
                max(a.y_max for a in self.spawn_areas),
            )

        exclusions = [(z.x_min, z.y_min, z.x_max, z.y_max) for z in self.exclusion_zones]

        self.position_strategy = OccupancySamplerStrategy(
            omap_config=omap_cfg,
            spawn_bounds=spawn_bounds,
            exclusion_rects=exclusions,
            grid_resolution=self.spawn_grid_resolution,
            safety_margin=self.robot_safety_margin,
            yaw_range=self.robot_init_yaw_range,
        )

    # ========== Scene Config Implementations ==========

    def get_terrain_cfg(self) -> TerrainImporterCfg:
        usd = self.usd_path if self.terrain_type == "usd" and self.usd_path else None
        return TerrainImporterCfg(
            prim_path="/World/ground",
            terrain_type=self.terrain_type if usd else "plane",
            terrain_generator=None,
            usd_path=usd,
            env_spacing=self.env_spacing,
            max_init_terrain_level=None,
            collision_group=-1,
            physics_material=sim_utils.RigidBodyMaterialCfg(
                friction_combine_mode="multiply",
                restitution_combine_mode="multiply",
                static_friction=self.terrain_friction,
                dynamic_friction=self.terrain_friction,
                restitution=self.terrain_restitution,
            ),
            debug_vis=False,
        )

    def get_obstacle_cfgs(self) -> dict[str, AssetBaseCfg]:
        return {}

    def get_light_cfgs(self) -> dict[str, AssetBaseCfg]:
        if self.use_usd_lighting:
            return {}
        return {
            "sky_light": AssetBaseCfg(
                prim_path="/World/skyLight",
                spawn=sim_utils.DomeLightCfg(
                    intensity=self.sky_light_intensity,
                    color=self.sky_color,
                    texture_file=self.sky_texture,
                    visible_in_primary_ray=self.sky_visible,
                ),
            ),
        }

    # ========== Helpers ==========

    def _get_playground(self) -> tuple[float, float, float, float] | None:
        """Return playground bounds, computing from spawn areas if needed."""
        if self.playground is not None:
            return self.playground
        if not self.spawn_areas:
            return None
        return (
            min(a.x_min for a in self.spawn_areas),
            min(a.y_min for a in self.spawn_areas),
            max(a.x_max for a in self.spawn_areas),
            max(a.y_max for a in self.spawn_areas),
        )

    def get_scene_asset_cfg(self) -> AssetBaseCfg | None:
        """Asset config for loading the USD scene separately from terrain."""
        if not self.usd_path:
            return None
        return AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Scene",
            spawn=sim_utils.UsdFileCfg(
                usd_path=self.usd_path,
                scale=self.usd_scale,
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    rigid_body_enabled=True,
                    kinematic_enabled=True,
                ),
                collision_props=sim_utils.CollisionPropertiesCfg(
                    collision_enabled=True,
                ),
            ),
            init_state=AssetBaseCfg.InitialStateCfg(
                pos=self.usd_position,
                rot=self.usd_rotation,
            ),
        )
